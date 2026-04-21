import { useState } from 'react'
import { Form, Input, Button, Typography, message } from 'antd'
import { UserOutlined, LockOutlined, MailOutlined, RobotOutlined, ArrowRightOutlined, StarOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { authAPI } from '../utils/api'

const { Text } = Typography

function Register() {
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const onFinish = async (values) => {
    setLoading(true)
    try {
      const response = await authAPI.register(values)
      // axios响应数据在response.data中
      if (response.data.success) {
        localStorage.setItem('token', response.data.data.token)
        localStorage.setItem('student_id', response.data.data.student_id)
        localStorage.setItem('username', response.data.data.username)
        // 清除旧的聊天记录，确保新用户不会看到其他用户的数据
        sessionStorage.removeItem('ai_tutor_chat_messages')
        message.success('注册成功！欢迎加入 AI Tutor')
        navigate('/ai-tutor')
      }
    } catch (error) {
      message.error(error.response?.data?.detail || '注册失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh', fontFamily: 'Inter, sans-serif' }}>

      {/* ── Left Aurora Panel ── */}
      <div style={{
        flex: '0 0 50%', position: 'relative', overflow: 'hidden',
        background: 'linear-gradient(145deg, #0891b2 0%, #6366f1 50%, #7c3aed 100%)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <div className="aurora-orb aurora-orb-1" style={{ width: 450, height: 450, background: 'radial-gradient(circle, rgba(255,255,255,0.12), transparent)', top: '-100px', right: '-80px' }} />
        <div className="aurora-orb aurora-orb-2" style={{ width: 380, height: 380, background: 'radial-gradient(circle, rgba(236,72,153,0.22), transparent)', bottom: '-60px', left: '-40px' }} />
        <div className="aurora-orb aurora-orb-3" style={{ width: 280, height: 280, background: 'radial-gradient(circle, rgba(16,185,129,0.2), transparent)', top: '50%', left: '50%', transform: 'translate(-50%,-50%)' }} />

        <div style={{ position: 'relative', zIndex: 1, padding: '48px', maxWidth: 440 }}>
          <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}
            style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 48 }}>
            <div style={{ width: 48, height: 48, borderRadius: 14, background: 'rgba(255,255,255,0.2)', backdropFilter: 'blur(10px)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <RobotOutlined style={{ fontSize: 24, color: '#fff' }} />
            </div>
            <span style={{ fontSize: 24, fontWeight: 800, color: '#fff' }}>AI Tutor</span>
          </motion.div>

          <motion.h2 initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.1 }}
            style={{ fontSize: 34, fontWeight: 900, color: '#fff', marginBottom: 16, lineHeight: 1.2 }}>
            开启你的智能<br />学习之旅
          </motion.h2>
          <motion.p initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.2 }}
            style={{ color: 'rgba(255,255,255,0.72)', fontSize: 16, marginBottom: 44, lineHeight: 1.6 }}>
            注册免费账户，立即体验 AI 导师的力量
          </motion.p>

          {/* Steps */}
          {[
            { num: '01', title: '创建账户', desc: '填写基本信息快速注册' },
            { num: '02', title: '设定学习目标', desc: '告诉 AI 你想学什么' },
            { num: '03', title: '生成知识图谱', desc: 'AI 自动规划学习路线' },
            { num: '04', title: '开始学习', desc: '与 AI 导师互动学习' },
          ].map((step, i) => (
            <motion.div key={i} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.5, delay: 0.3 + i * 0.08 }}
              style={{ display: 'flex', gap: 16, marginBottom: 20 }}>
              <div style={{ width: 36, height: 36, borderRadius: 10, background: 'rgba(255,255,255,0.15)', backdropFilter: 'blur(8px)', border: '1px solid rgba(255,255,255,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <span style={{ color: '#fff', fontWeight: 800, fontSize: 12 }}>{step.num}</span>
              </div>
              <div>
                <div style={{ color: '#fff', fontWeight: 600, fontSize: 14 }}>{step.title}</div>
                <div style={{ color: 'rgba(255,255,255,0.6)', fontSize: 12.5 }}>{step.desc}</div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>

      {/* ── Right Form Panel ── */}
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f8faff', padding: '40px 48px', overflowY: 'auto' }}>
        <motion.div initial={{ opacity: 0, x: 24 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.6, delay: 0.2 }}
          style={{ width: '100%', maxWidth: 380 }}>

          <button onClick={() => navigate('/')} style={{ background: 'none', border: 'none', color: '#94a3b8', fontSize: 13, cursor: 'pointer', marginBottom: 28, display: 'flex', alignItems: 'center', gap: 4, padding: 0 }}>
            ← 返回首页
          </button>

          <h2 style={{ fontSize: 28, fontWeight: 800, color: '#0f172a', marginBottom: 8 }}>创建账户</h2>
          <p style={{ color: '#64748b', fontSize: 15, marginBottom: 32 }}>只需几步，立即开启学习之旅</p>

          <Form name="register" onFinish={onFinish} autoComplete="off" size="large" layout="vertical">
            <Form.Item name="username" label={<span style={{ color: '#374151', fontWeight: 600, fontSize: 13 }}>用户名</span>}
              rules={[{ required: true, message: '请输入用户名' }, { min: 3, message: '用户名至少3个字符' }]}>
              <Input prefix={<UserOutlined style={{ color: '#a5b4fc' }} />} placeholder="用于登录，不可修改"
                style={{ height: 46, borderRadius: 10, border: '1.5px solid #e2e8f0', background: '#fff' }} />
            </Form.Item>

            <Form.Item name="nickname" label={<span style={{ color: '#374151', fontWeight: 600, fontSize: 13 }}>昵称</span>}
              rules={[{ required: true, message: '请输入昵称' }]}>
              <Input prefix={<UserOutlined style={{ color: '#a5b4fc' }} />} placeholder="显示名称，可修改"
                style={{ height: 46, borderRadius: 10, border: '1.5px solid #e2e8f0', background: '#fff' }} />
            </Form.Item>

            <Form.Item name="email" label={<span style={{ color: '#374151', fontWeight: 600, fontSize: 13 }}>邮箱（可选）</span>}
              rules={[{ type: 'email', message: '请输入有效的邮箱地址' }]}>
              <Input prefix={<MailOutlined style={{ color: '#a5b4fc' }} />} placeholder="用于找回密码（可选）"
                style={{ height: 46, borderRadius: 10, border: '1.5px solid #e2e8f0', background: '#fff' }} />
            </Form.Item>

            <Form.Item name="password" label={<span style={{ color: '#374151', fontWeight: 600, fontSize: 13 }}>密码</span>}
              rules={[{ required: true, message: '请输入密码' }, { min: 6, message: '密码至少6个字符' }]}>
              <Input.Password prefix={<LockOutlined style={{ color: '#a5b4fc' }} />} placeholder="至少6个字符"
                style={{ height: 46, borderRadius: 10, border: '1.5px solid #e2e8f0', background: '#fff' }} />
            </Form.Item>

            <Form.Item name="confirmPassword" label={<span style={{ color: '#374151', fontWeight: 600, fontSize: 13 }}>确认密码</span>}
              dependencies={['password']}
              rules={[
                { required: true, message: '请确认密码' },
                ({ getFieldValue }) => ({
                  validator(_, value) {
                    if (!value || getFieldValue('password') === value) return Promise.resolve()
                    return Promise.reject(new Error('两次输入的密码不一致'))
                  },
                }),
              ]}>
              <Input.Password prefix={<LockOutlined style={{ color: '#a5b4fc' }} />} placeholder="再次输入密码"
                style={{ height: 46, borderRadius: 10, border: '1.5px solid #e2e8f0', background: '#fff' }} />
            </Form.Item>

            <Form.Item style={{ marginBottom: 16, marginTop: 8 }}>
              <Button htmlType="submit" loading={loading} block
                style={{
                  height: 50, borderRadius: 12, border: 'none',
                  background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                  color: '#fff', fontSize: 16, fontWeight: 700,
                  boxShadow: '0 6px 20px rgba(99,102,241,0.4)',
                }}>
                {loading ? '注册中...' : '立即注册'}
              </Button>
            </Form.Item>
          </Form>

          <div style={{ borderTop: '1px solid #f1f5f9', paddingTop: 20, textAlign: 'center' }}>
            <Text style={{ color: '#94a3b8', fontSize: 14 }}>已有账户？</Text>
            <button onClick={() => navigate('/login')} style={{ background: 'none', border: 'none', color: '#6366f1', fontWeight: 700, fontSize: 14, cursor: 'pointer', padding: '0 6px' }}>
              立即登录 →
            </button>
          </div>
        </motion.div>
      </div>
    </div>
  )
}

export default Register
