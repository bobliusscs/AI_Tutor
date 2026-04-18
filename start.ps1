# MindGuide 快速启动脚本

Write-Host "====================================" -ForegroundColor Cyan
Write-Host "  MindGuide AI 家教系统 - 启动脚本" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Python
Write-Host "[1/4] 检查 Python 环境..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version
    Write-Host "✓ Python 已安装：$pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ 错误：未找到 Python，请先安装 Python 3.10+" -ForegroundColor Red
    exit 1
}

# 检查 Node.js
Write-Host "[2/4] 检查 Node.js 环境..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version
    Write-Host "✓ Node.js 已安装：$nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ 错误：未找到 Node.js，请先安装 Node.js" -ForegroundColor Red
    exit 1
}

# 启动后端
Write-Host "[3/4] 启动后端服务器..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; .\venv\Scripts\Activate.ps1; uvicorn app.main:app --reload"
Write-Host "✓ 后端将在 http://localhost:8000 启动" -ForegroundColor Green
Write-Host "  API 文档：http://localhost:8000/docs" -ForegroundColor Green

# 等待 3 秒
Start-Sleep -Seconds 3

# 启动前端
Write-Host "[4/4] 启动前端开发服务器..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev"
Write-Host "✓ 前端将在 http://localhost:5173 启动" -ForegroundColor Green

Write-Host ""
Write-Host "====================================" -ForegroundColor Cyan
Write-Host "  启动完成！" -ForegroundColor Green
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "访问地址：" -ForegroundColor Cyan
Write-Host "  前端界面：http://localhost:5173" -ForegroundColor White
Write-Host "  后端 API:  http://localhost:8000" -ForegroundColor White
Write-Host "  API 文档： http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "按任意键退出此窗口..." -ForegroundColor Gray
