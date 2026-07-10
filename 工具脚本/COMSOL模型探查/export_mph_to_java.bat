@echo off
REM 通过 COMSOL 命令行导出 Java 代码
REM 需要 COMSOL 已安装并配置了环境变量

echo ========================================
echo 导出 COMSOL 模型为 Java 代码
echo ========================================

set MPH_FILE=f:\pyProject\fipy_naca0012_2.0\大论文初稿\plate_fin_heat_exchanger.mph
set JAVA_FILE=f:\pyProject\fipy_naca0012_2.0\大论文初稿\plate_fin_model.java

echo.
echo [INFO] MPH 文件: %MPH_FILE%
echo [INFO] 输出 Java: %JAVA_FILE%
echo.

REM 使用 COMSOL 命令行工具导出
REM 注意：这需要 COMSOL 的 mphbin 工具支持
comsol batch -input "%MPH_FILE%" -exportjava "%JAVA_FILE%"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] Java 代码导出成功！
    echo [INFO] 文件位置: %JAVA_FILE%
) else (
    echo.
    echo [ERROR] 导出失败，请尝试手动在 COMSOL Desktop 中导出
    echo.
    echo 手动导出步骤:
    echo 1. 打开 COMSOL Desktop
    echo 2. 加载 %MPH_FILE%
    echo 3. File ^> Export ^> Model Method for Java
    echo 4. 保存到 %JAVA_FILE%
)

pause
