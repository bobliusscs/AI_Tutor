import { useState } from 'react'
import { Form, Input, Button, Typography, message } from 'antd'
import { UserOutlined, LockOutlined, RobotOutlined, ArrowRightOutlined, CheckCircleOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { authAPI } from '../utils/api'

const { Text } = Typography

const features = [
  { icon: '🧠', title: 'AI 智能答疑', desc: '随时随地向 AI 导师提问' },
  { icon: '🗺️', title: '可视化知识图谱', desc: '清晰呈现知识点关联结构' },
  { icon: '📊', title: '学情深度分析', desc: '精准识别薄弱点，科学提升' },
  { icon: '🎯', title: '个性化学习计划', desc: 'AI 定制专属学习路线' },
]

function Login() {
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const onFinish = async (values) => {
    setLoading(true)
    try {
      const response = await authAPI.login(values)
      const data = response.data || response
      if (data.success) {
        localStorage.setItem('token', data.data?.token || data.token)
        localStorage.setItem('student_id', data.data?.student_id || data.student_id)
        localStorage.setItem('username', data.data?.username || data.username)
        localStorage.setItem('nickname', data.data?.nickname || data.data?.username || data.username)
        // 清除旧的聊天记录，确保新用户不会看到其他用户的数据
        sessionStorage.removeItem('ai_tutor_chat_messages')
        message.success('登录成功！')
        navigate('/ai-tutor')
      } else {
        message.error(data.message || '登录失败')
      }
    } catch (error) {
      message.error(error.response?.data?.detail || error.response?.data?.message || error.message || '登录失败，请检查用户名和密码')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh', fontFamily: 'Inter, sans-serif' }}>

      {/* ── Left Aurora Panel ── */}
      <div style={{
        flex: '0 0 55%', position: 'relative', overflow: 'hidden',
        background: 'linear-gradient(145deg, #4f46e5 0%, #7c3aed 40%, #0891b2 100%)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        {/* Aurora orbs */}
        <div className="aurora-orb aurora-orb-1" style={{ width: 500, height: 500, background: 'radial-gradient(circle, rgba(255,255,255,0.12), transparent)', top: '-150px', left: '-100px' }} />
        <div className="aurora-orb aurora-orb-2" style={{ width: 380, height: 380, background: 'radial-gradient(circle, rgba(6,182,212,0.25), transparent)', bottom: '-80px', right: '-60px' }} />
        <div className="aurora-orb aurora-orb-3" style={{ width: 300, height: 300, background: 'radial-gradient(circle, rgba(236,72,153,0.2), transparent)', top: '40%', left: '50%', transform: 'translate(-50%,-50%)' }} />

        <div style={{ position: 'relative', zIndex: 1, padding: '48px', maxWidth: 460 }}>
          {/* Logo */}
          <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}
            style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 52 }}>
            <div style={{ width: 48, height: 48, borderRadius: 14, background: 'rgba(255,255,255,0.2)', backdropFilter: 'blur(10px)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 4px 16px rgba(0,0,0,0.1)' }}>
              <RobotOutlined style={{ fontSize: 24, color: '#fff' }} />
            </div>
            <span style={{ fontSize: 24, fontWeight: 800, color: '#fff', letterSpacing: '-0.5px' }}>AI Tutor</span>
          </motion.div>

          <motion.h2 initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.1 }}
            style={{ fontSize: 36, fontWeight: 900, color: '#fff', marginBottom: 16, lineHeight: 1.2, letterSpacing: '-0.5px' }}>
            让 AI 成为你最好的<br />学习伙伴
          </motion.h2>
          <motion.p initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.2 }}
            style={{ color: 'rgba(255,255,255,0.7)', fontSize: 16, marginBottom: 44, lineHeight: 1.6 }}>
            个性化知识图谱 · 智能学习规划 · 24/7 在线答疑
          </motion.p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {features.map((f, i) => (
              <motion.div key={i} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.5, delay: 0.3 + i * 0.1 }}
                style={{ display: 'flex', alignItems: 'center', gap: 16, padding: '14px 20px', borderRadius: 14, background: 'rgba(255,255,255,0.1)', backdropFilter: 'blur(10px)', border: '1px solid rgba(255,255,255,0.15)' }}>
                <span style={{ fontSize: 24 }}>{f.icon}</span>
                <div>
                  <div style={{ color: '#fff', fontWeight: 600, fontSize: 14 }}>{f.title}</div>
                  <div style={{ color: 'rgba(255,255,255,0.6)', fontSize: 12.5 }}>{f.desc}</div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Right Form Panel ── */}
      <div style={{
        flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: '#f8faff', padding: '40px 48px',
      }}>
        <motion.div initial={{ opacity: 0, x: 24 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.6, delay: 0.2 }}
          style={{ width: '100%', maxWidth: 380 }}>

          {/* Back to home */}
          <button onClick={() => navigate('/')} style={{ background: 'none', border: 'none', color: '#94a3b8', fontSize: 13, cursor: 'pointer', marginBottom: 32, display: 'flex', alignItems: 'center', gap: 4, padding: 0 }}>
            ← 返回首页
          </button>

          <h2 style={{ fontSize: 28, fontWeight: 800, color: '#0f172a', marginBottom: 8, letterSpacing: '-0.3px' }}>欢迎回来</h2>
          <p style={{ color: '#64748b', fontSize: 15, marginBottom: 36 }}>登录你的 AI Tutor 账户，继续学习之旅</p>

          <Form name="login" onFinish={onFinish} autoComplete="off" size="large" layout="vertical">
            <Form.Item name="username" label={<span style={{ color: '#374151', fontWeight: 600, fontSize: 13 }}>用户名</span>} rules={[{ required: true, message: '请输入用户名' }]}>
              <Input prefix={<UserOutlined style={{ color: '#a5b4fc' }} />} placeholder="请输入用户名"
                style={{ height: 48, borderRadius: 10, border: '1.5px solid #e2e8f0', background: '#fff', fontSize: 14 }} />
            </Form.Item>

            <Form.Item name="password" label={<span style={{ color: '#374151', fontWeight: 600, fontSize: 13 }}>密码</span>} rules={[{ required: true, message: '请输入密码' }]}>
              <Input.Password prefix={<LockOutlined style={{ color: '#a5b4fc' }} />} placeholder="请输入密码"
                style={{ height: 48, borderRadius: 10, border: '1.5px solid #e2e8f0', background: '#fff', fontSize: 14 }} />
            </Form.Item>

            <Form.Item style={{ marginBottom: 16, marginTop: 8 }}>
              <Button htmlType="submit" loading={loading} block
                style={{
                  height: 50, borderRadius: 12, border: 'none',
                  background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                  color: '#fff', fontSize: 16, fontWeight: 700,
                  boxShadow: '0 6px 20px rgba(99,102,241,0.4)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                }}
              >
                {loading ? '登录中...' : <><span>登录</span> <ArrowRightOutlined /></>}
              </Button>
            </Form.Item>
          </Form>

          <div style={{ borderTop: '1px solid #f1f5f9', paddingTop: 24, marginTop: 8 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
              <Text style={{ color: '#94a3b8', fontSize: 14 }}>还没有账户？</Text>
              <button onClick={() => navigate('/register')} style={{ background: 'none', border: 'none', color: '#6366f1', fontWeight: 700, fontSize: 14, cursor: 'pointer', padding: '0 4px' }}>
                立即注册 →
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  )
}

export default Login
