# 每 3 天把云数据库备份到本机

目标：腾讯云上的 `campus_match.db` → 本机 `D:\backup\campus-match\`

原理：**本机主动拉**（Windows 计划任务），不是云往你电脑推。  
因此：**到点时电脑要开机且能上网**；关机就会跳过（下次开机不会自动补跑，除非你手动执行脚本）。

## 一次性准备

### 1. 把本机 SSH 公钥放到服务器（免密）

本机 PowerShell：

```powershell
Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub
```

复制整行，再到**服务器**执行（把 `粘贴公钥整行` 换成你的）：

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
echo '粘贴公钥整行' >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

本机测通：

```powershell
ssh ubuntu@106.53.82.216 "echo ok"
```

不应再要密码。

### 2. 手动试跑一次备份

```powershell
powershell -ExecutionPolicy Bypass -File D:\claude\projects\campus-match\scripts\backup-from-cloud.ps1
```

成功后看：`D:\backup\campus-match\campus_match_*.db` 和 `backup.log`。

### 3. 注册「每 3 天」计划任务

管理员 PowerShell：

```powershell
schtasks /Create /F `
  /TN "CampusMatch-DB-Backup" `
  /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"D:\claude\projects\campus-match\scripts\backup-from-cloud.ps1`"" `
  /SC DAILY /MO 3 /ST 15:30 `
  /RL LIMITED
```

含义：每 3 天的 **下午 15:30** 跑一次（电脑通常开机时段）。

查看 / 立刻跑一次 / 删除：

```powershell
schtasks /Query /TN "CampusMatch-DB-Backup" /V /FO LIST
schtasks /Run /TN "CampusMatch-DB-Backup"
schtasks /Delete /TN "CampusMatch-DB-Backup" /F
```

## 保留策略

脚本默认只保留约 **60 天**内的 `.db` 文件，更早的会删掉。可改脚本里的 `$KeepDays`。

## 还原（出事时）

1. 停云上服务：`sudo systemctl stop campus-match`
2. 上传备份覆盖：  
   `scp D:\backup\campus-match\某天.db ubuntu@106.53.82.216:/opt/campus-match/instance/campus_match.db`
3. 启动：`sudo systemctl start campus-match`
