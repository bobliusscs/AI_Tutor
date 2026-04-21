import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { ConfigProvider, App as AntApp } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: '#6366f1',
          colorSuccess: '#10b981',
          colorWarning: '#f59e0b',
          colorError: '#f43f5e',
          colorInfo: '#06b6d4',
          colorLink: '#6366f1',
          borderRadius: 8,
          borderRadiusLG: 12,
          borderRadiusSM: 6,
          fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Noto Sans SC', sans-serif",
          fontSize: 14,
          colorBgContainer: '#ffffff',
          colorBgElevated: '#ffffff',
          colorBorder: '#e2e8f0',
          colorBorderSecondary: '#f1f5f9',
          colorTextBase: '#0f172a',
          colorTextSecondary: '#475569',
          colorTextTertiary: '#94a3b8',
          boxShadow: '0 4px 24px rgba(99, 102, 241, 0.08), 0 1px 8px rgba(0, 0, 0, 0.04)',
          boxShadowSecondary: '0 12px 40px rgba(99, 102, 241, 0.14), 0 4px 16px rgba(0, 0, 0, 0.06)',
        },
        components: {
          Button: { borderRadius: 8, fontWeight: 500 },
          Card: { borderRadiusLG: 16 },
          Menu: { itemBorderRadius: 8, itemMarginInline: 6 },
          Input: { borderRadius: 8 },
          Select: { borderRadius: 8 },
          Modal: { borderRadiusLG: 20 },
        },
      }}
    >
      <AntApp>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </AntApp>
    </ConfigProvider>
  </React.StrictMode>,
)
