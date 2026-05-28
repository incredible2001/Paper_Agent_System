@echo off
echo ========================================
echo Paper Agent System - 项目备份脚本
echo ========================================
echo.

REM 获取当前日期和时间
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set datetime=%datetime:~0,8%_%datetime:~8,6%

REM 创建备份目录
set backup_dir=..\Paper_Agent_Backup_%datetime%
echo 创建备份目录: %backup_dir%
mkdir "%backup_dir%"

REM 复制项目文件（排除 .venv 和大型数据文件）
echo.
echo 正在备份项目文件...
xcopy /E /I /Y /EXCLUDE:backup_exclude.txt . "%backup_dir%\Paper_Agent_System"

echo.
echo ========================================
echo 备份完成！
echo 备份位置: %backup_dir%
echo ========================================
echo.
pause
