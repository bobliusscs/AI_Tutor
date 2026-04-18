import { Component } from 'react'
import { Result, Button, Typography, Space, Card } from 'antd'
import { ReloadOutlined, HomeOutlined, BugOutlined } from '@ant-design/icons'

const { Text, Paragraph } = Typography

// 错误边界组件
export class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { 
      hasError: false, 
      error: null,
      errorInfo: null
    }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('Error caught by boundary:', error, errorInfo)
    this.setState({ errorInfo })
    
    // 可以在这里发送错误报告到服务器
    this.reportError(error, errorInfo)
  }

  reportError(error, errorInfo) {
    // 错误上报逻辑
    if (process.env.NODE_ENV === 'production') {
      // 发送到错误监控服务
      console.log('Reporting error:', {
        error: error?.toString(),
        stack: error?.stack,
        componentStack: errorInfo?.componentStack,
        url: window.location.href,
        timestamp: new Date().toISOString()
      })
    }
  }

  handleReload = () => {
    window.location.reload()
  }

  handleGoHome = () => {
    window.location.href = '/'
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ 
          minHeight: '100vh', 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          padding: 24,
          background: '#f5f5f5'
        }}>
          <Card style={{ maxWidth: 600, width: '100%' }}>
            <Result
              status="error"
              title="页面出现错误"
              subTitle="抱歉，应用程序遇到了一些问题。我们已经记录了此错误。"
              icon={<BugOutlined style={{ color: '#ff4d4f' }} />}
              extra={[
                <Space key="actions" direction="vertical" style={{ width: '100%' }}>
                  <Button 
                    type="primary" 
                    icon={<ReloadOutlined />}
                    onClick={this.handleReload}
                    block
                  >
                    重新加载页面
                  </Button>
                  <Button 
                    icon={<HomeOutlined />}
                    onClick={this.handleGoHome}
                    block
                  >
                    返回首页
                  </Button>
                </Space>
              ]}
            >
              {process.env.NODE_ENV === 'development' && (
                <div style={{ 
                  background: '#fff2f0', 
                  border: '1px solid #ffccc7',
                  borderRadius: 8,
                  padding: 16,
                  marginTop: 24
                }}>
                  <Text strong style={{ color: '#cf1322' }}>
                    开发环境错误详情：
                  </Text>
                  <Paragraph style={{ marginTop: 8 }}>
                    <Text code style={{ display: 'block', marginBottom: 8 }}>
                      {this.state.error?.toString()}
                    </Text>
                    <pre style={{ 
                      fontSize: 12, 
                      overflow: 'auto',
                      maxHeight: 200,
                      background: '#fff',
                      padding: 8,
                      borderRadius: 4
                    }}>
                      {this.state.errorInfo?.componentStack}
                    </pre>
                  </Paragraph>
                </div>
              )}
            </Result>
          </Card>
        </div>
      )
    }

    return this.props.children
  }
}

