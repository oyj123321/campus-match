"""Pure report presentation: scopes, evidence-based comparisons and alerts."""
from copy import deepcopy

MIN_SAMPLE = 20


def build_analysis(reports, labels, days=90, school='', round_id=None):
    from matching_analytics import report_tips
    schools = sorted({s['school'] for r in reports for s in r.get('schools', [])})
    invalid_school = bool(school and school not in schools)
    scoped = []
    for original in reports:
        row = deepcopy(original)
        if school:
            member = next((s for s in row.get('schools', []) if s['school'] == school), None)
            # Missing school data is unknown, never a fabricated zero.
            if member is None:
                row['unavailable'] = True
            else:
                for key in ('age_missing', 'no_candidates', 'one_candidate', 'many_candidates',
                            'contested_sole', 'history_exhausted', 'reasons'):
                    row.pop(key, None)
                row.update(member)
                row['unmatched'] = row['participants'] - row['matched']
                row['rate'] = round(100 * row['matched'] / row['participants'], 1) if row['participants'] else 0
                row.pop('quota_excluded', None)  # available only for the full pool
                if 'reasons' not in member:
                    row['diagnosis_unavailable'] = True
                    row.pop('reasons', None)
        scoped.append(row)
    completed = [r for r in scoped if r['status'] == 'completed' and not r.get('unavailable')]
    selected = next((r for r in scoped if r['id'] == round_id), None) if round_id else next(iter(completed), None)
    latest = selected if selected and selected['status'] == 'completed' and not selected.get('unavailable') else None
    comparison = None
    alerts = []
    # Operational failures are shown for the whole batch, regardless of school scope.
    if reports and reports[0]['status'] == 'failed':
        alerts.append({'level': 'warning', 'text': f"最近轮次 #{reports[0]['id']} 执行失败：请检查执行日志；部分配对可能已写入。"})
    elif reports and reports[0]['status'] == 'running':
        stale = reports[0].get('elapsed_minutes', 0) >= 60
        alerts.append({'level': 'warning' if stale else 'info', 'text':
            f"最近轮次 #{reports[0]['id']} 超过 60 分钟未完成，请核查是否中断。" if stale else
            f"最近轮次 #{reports[0]['id']} 正在执行，结果完成后刷新查看。"})
    if any(r.get('unavailable') for r in reports):
        alerts.append({'level': 'warning', 'text': '存在无法读取的报告，已标为数据缺失；不参与比较。'})
    if invalid_school:
        alerts.append({'level': 'info', 'text': '所选学校在此时间范围内没有记录。'})
    if round_id and selected is None:
        alerts.append({'level': 'info', 'text': '所选轮次不在当前时间范围或最近 100 轮内。'})
    if latest:
        prior = [r for r in completed if r['id'] < latest['id'] and r.get('policy') == latest.get('policy')
                 and r.get('version', 1) == latest.get('version', 1) and r.get('participants', 0) > 0]
        if latest.get('participants', 0) > 0 and prior:
            previous = prior[0]
            baseline = prior[:5]
            n = sum(r['participants'] for r in baseline)
            rate = round(100 * sum(r['matched'] for r in baseline) / n, 1)
            comparison = {'previous_id': previous['id'], 'delta': round(latest['rate'] - previous['rate'], 1),
                          'baseline': rate, 'baseline_n': n, 'baseline_rounds': len(baseline),
                          'baseline_delta': round(latest['rate'] - rate, 1)}
            # Require two consecutive declines, each with sufficient sample, against older rounds.
            older = prior[1:6]
            sufficient = (latest['participants'] >= MIN_SAMPLE and previous['participants'] >= MIN_SAMPLE
                          and len(older) >= 3 and all(r['participants'] >= MIN_SAMPLE for r in older))
            if sufficient:
                historical = 100 * sum(r['matched'] for r in older) / sum(r['participants'] for r in older)
                if latest['rate'] <= historical - 10 and previous['rate'] <= historical - 10:
                    alerts.append({'level': 'warning', 'text':
                        f"连续两轮匹配率比此前 {len(older)} 轮加权基准 {historical:.1f}% 低至少 10 个百分点。请查看未匹配原因与供需结构；这不是因果结论。"})
        if latest.get('participants', 0) < MIN_SAMPLE:
            alerts.append({'level': 'info', 'text': f'本轮样本少于 {MIN_SAMPLE} 人，暂不足以判断稳定趋势。'})
        elif comparison is None or comparison['baseline_rounds'] < 3:
            alerts.append({'level': 'info', 'text': '可比较的历史轮次不足，先积累基准。'})
    tips = report_tips(latest)
    if latest and latest.get('contested_sole'):
        tips.insert(0, f"{latest['contested_sole']} 人的唯一候选也被其他人作为唯一候选；存在明确的一对一供需竞争。")
    if latest and latest.get('history_exhausted'):
        tips.append(f"{latest['history_exhausted']} 人当前无候选，但存在其他条件合适的历史对象；优先补充新参与者，保留不重复配对规则。")
    trend = list(reversed(completed[:20]))
    return dict(rounds=scoped, latest=latest, selected=selected, labels=labels, tips=tips,
                alerts=alerts, comparison=comparison, schools=schools, school=school,
                days=days, round_id=round_id, trend=trend,
                max_participants=max([r.get('participants', 0) for r in trend] + [1]))
