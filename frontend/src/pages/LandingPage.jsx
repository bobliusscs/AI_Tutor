import { useNavigate } from 'react-router-dom'
import { motion, useInView } from 'framer-motion'
import { useRef } from 'react'
import {
  RocketOutlined,
  TeamOutlined,
  BookOutlined,
  RobotOutlined,
  CheckCircleOutlined,
  ArrowRightOutlined,
  ThunderboltOutlined,
  LineChartOutlined,
  BulbOutlined,
} from '@ant-design/icons'

/* ── Reusable Aurora background orbs ── */
function AuroraBackground({ children, style = {} }) {
  return (
    <div style={{ position: 'relative', overflow: 'hidden', ...style }}>
      <div className="aurora-orb aurora-orb-1"
        style={{ width: 500, height: 500, background: 'radial-gradient(circle, rgba(99,102,241,0.55), transparent)', top: '-100px', left: '-120px' }} />
      <div className="aurora-orb aurora-orb-2"
        style={{ width: 420, height: 420, background: 'radial-gradient(circle, rgba(6,182,212,0.45), transparent)', top: '60px', right: '-80px' }} />
      <div className="aurora-orb aurora-orb-3"
        style={{ width: 350, height: 350, background: 'radial-gradient(circle, rgba(236,72,153,0.35), transparent)', bottom: '0', left: '30%' }} />
      <div className="aurora-orb aurora-orb-4"
        style={{ width: 280, height: 280, background: 'radial-gradient(circle, rgba(16,185,129,0.38), transparent)', bottom: '-60px', right: '15%' }} />
      {children}
    </div>
  )
}

/* ── Animated counter ── */
function StatCard({ value, label, gradient, delay = 0 }) {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true })
  return (
    <motion.div ref={ref}
      initial={{ opacity: 0, y: 24 }}
      animate={isInView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.6, delay }}
      style={{
        background: 'rgba(255,255,255,0.85)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        border: '1px solid rgba(255,255,255,0.7)',
        borderRadius: 20,
        padding: '28px 32px',
        textAlign: 'center',
        boxShadow: '0 8px 32px rgba(99,102,241,0.1)',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: 4, background: gradient, borderRadius: '0 0 20px 20px' }} />
      <div style={{ fontSize: 36, fontWeight: 800, background: gradient, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', lineHeight: 1 }}>
        {value}
      </div>
      <div style={{ marginTop: 8, color: '#64748b', fontSize: 14, fontWeight: 500 }}>{label}</div>
    </motion.div>
  )
}

const features = [
  {
    icon: <RobotOutlined />,
    title: 'AI 智能辅导',
    desc: '基于先进大语言模型，提供个性化的实时学习指导与答疑',
    gradient: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
    size: 'large',
  },
  {
    icon: <BookOutlined />,
    title: '知识图谱',
    desc: '可视化知识网络，清晰呈现知识点关联',
    gradient: 'linear-gradient(135deg, #06b6d4, #10b981)',
    size: 'normal',
  },
  {
    icon: <TeamOutlined />,
    title: '智能学习计划',
    desc: 'AI 根据你的掌握度定制专属路线',
    gradient: 'linear-gradient(135deg, #8b5cf6, #ec4899)',
    size: 'normal',
  },
  {
    icon: <RocketOutlined />,
    title: '科学复习',
    desc: '基于遗忘曲线算法，高效巩固知识',
    gradient: 'linear-gradient(135deg, #f59e0b, #ef4444)',
    size: 'normal',
  },
  {
    icon: <LineChartOutlined />,
    title: '学情分析',
    desc: '深度分析薄弱点，可视化学习进度',
    gradient: 'linear-gradient(135deg, #10b981, #06b6d4)',
    size: 'normal',
  },
  {
    icon: <ThunderboltOutlined />,
    title: '随时随地',
    desc: '24/7 全天候 AI 家教随时在线',
    gradient: 'linear-gradient(135deg, #ec4899, #6366f1)',
    size: 'wide',
  },
]

const testimonials = [
  {
    name: '张同学',
    role: '高中生',
    content: 'AI Tutor 帮我梳理了数学知识体系，成绩明显提升，知识图谱功能真的太直观了！',
    avatar: '张',
    color: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
  },
  {
    name: '李同学',
    role: '大学生',
    content: '个性化的学习计划让我不再迷茫，AI 导师的解答质量超出预期，强烈推荐！',
    avatar: '李',
    color: 'linear-gradient(135deg, #06b6d4, #10b981)',
  },
  {
    name: '王同学',
    role: '自学者',
    content: '随时问随时答，比找人辅导方便太多了。学情分析功能帮我找到了薄弱环节。',
    avatar: '王',
    color: 'linear-gradient(135deg, #f59e0b, #ec4899)',
  },
]

function LandingPage() {
  const navigate = useNavigate()

  const fadeUp = (delay = 0) => ({
    initial: { opacity: 0, y: 28 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.7, delay, ease: [0.22, 1, 0.36, 1] },
  })

  return (
    <div style={{ minHeight: '100vh', background: '#f8faff', fontFamily: 'Inter, sans-serif' }}>

      {/* ── Navbar ── */}
      <nav style={{
        position: 'sticky', top: 0, zIndex: 100,
        padding: '0 60px',
        height: 68,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        background: 'rgba(248,250,255,0.85)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        borderBottom: '1px solid rgba(226,232,240,0.6)',
        boxShadow: '0 1px 20px rgba(99,102,241,0.06)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 38, height: 38, borderRadius: 10,
            background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 4px 12px rgba(99,102,241,0.4)',
          }}>
            <RobotOutlined style={{ fontSize: 20, color: '#fff' }} />
          </div>
          <span style={{ fontSize: 20, fontWeight: 700, background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            AI Tutor
          </span>
        </div>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <button onClick={() => navigate('/login')} style={{
            padding: '8px 22px', borderRadius: 8, border: '1.5px solid #e2e8f0',
            background: 'transparent', fontSize: 14, fontWeight: 500, cursor: 'pointer',
            color: '#475569', transition: 'all 0.2s',
          }}
            onMouseEnter={e => { e.target.style.borderColor = '#6366f1'; e.target.style.color = '#6366f1' }}
            onMouseLeave={e => { e.target.style.borderColor = '#e2e8f0'; e.target.style.color = '#475569' }}
          >
            登录
          </button>
          <button onClick={() => navigate('/register')} className="btn-gradient"
            style={{ padding: '8px 22px', borderRadius: 8, fontSize: 14, fontWeight: 600, cursor: 'pointer', color: '#fff', border: 'none', background: 'linear-gradient(135deg,#6366f1,#8b5cf6)', boxShadow: '0 4px 12px rgba(99,102,241,0.38)' }}>
            免费注册
          </button>
        </div>
      </nav>

      {/* ── Hero ── */}
      <AuroraBackground style={{ minHeight: '88vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ position: 'relative', zIndex: 1, textAlign: 'center', padding: '60px 24px', maxWidth: 860, margin: '0 auto' }}>
          <motion.div {...fadeUp(0.1)}>
            <span style={{
              display: 'inline-flex', alignItems: 'center', gap: 6,
              padding: '6px 16px', borderRadius: 99,
              background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.25)',
              fontSize: 13, fontWeight: 600, color: '#6366f1', marginBottom: 28,
            }}>
              <ThunderboltOutlined style={{ fontSize: 12 }} />
              由先进 AI 技术驱动
            </span>
          </motion.div>

          <motion.h1 {...fadeUp(0.2)} style={{ fontSize: 'clamp(40px, 6vw, 72px)', fontWeight: 900, lineHeight: 1.1, marginBottom: 24, color: '#0f172a', letterSpacing: '-1.5px' }}>
            你的私人
            <span className="gradient-text-aurora"> AI 学习导师</span>
          </motion.h1>

          <motion.p {...fadeUp(0.3)} style={{ fontSize: 18, color: '#64748b', lineHeight: 1.7, maxWidth: 600, margin: '0 auto 40px' }}>
            借助大语言模型，为你构建个性化知识图谱，制定专属学习计划，<br />随时随地解答疑惑，让学习更高效、更有趣。
          </motion.p>

          <motion.div {...fadeUp(0.4)} style={{ display: 'flex', gap: 14, justifyContent: 'center', flexWrap: 'wrap' }}>
            <button onClick={() => navigate('/register')} style={{
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '14px 36px', borderRadius: 12, border: 'none',
              background: 'linear-gradient(135deg,#6366f1,#8b5cf6)',
              color: '#fff', fontSize: 16, fontWeight: 700, cursor: 'pointer',
              boxShadow: '0 6px 24px rgba(99,102,241,0.45)',
              transition: 'all 0.2s',
            }}
              onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = '0 10px 32px rgba(99,102,241,0.55)' }}
              onMouseLeave={e => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow = '0 6px 24px rgba(99,102,241,0.45)' }}
            >
              立即免费体验 <ArrowRightOutlined />
            </button>
            <button onClick={() => document.getElementById('features').scrollIntoView({ behavior: 'smooth' })} style={{
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '14px 36px', borderRadius: 12,
              border: '1.5px solid rgba(99,102,241,0.3)',
              background: 'rgba(255,255,255,0.8)', backdropFilter: 'blur(10px)',
              color: '#6366f1', fontSize: 16, fontWeight: 600, cursor: 'pointer',
              transition: 'all 0.2s',
            }}
              onMouseEnter={e => { e.currentTarget.style.background = 'rgba(99,102,241,0.08)'; e.currentTarget.style.transform = 'translateY(-2px)' }}
              onMouseLeave={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.8)'; e.currentTarget.style.transform = 'translateY(0)' }}
            >
              了解功能
            </button>
          </motion.div>

          {/* Floating mini cards */}
          <motion.div {...fadeUp(0.6)} style={{ display: 'flex', gap: 16, justifyContent: 'center', marginTop: 56, flexWrap: 'wrap' }}>
            {[
              { icon: '🧠', text: '智能答疑' },
              { icon: '🗺️', text: '知识图谱' },
              { icon: '📊', text: '学情分析' },
              { icon: '🎯', text: '个性规划' },
            ].map((item, i) => (
              <div key={i} style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '10px 18px', borderRadius: 12,
                background: 'rgba(255,255,255,0.85)', backdropFilter: 'blur(12px)',
                border: '1px solid rgba(255,255,255,0.7)',
                boxShadow: '0 4px 16px rgba(99,102,241,0.08)',
                fontSize: 14, fontWeight: 500, color: '#374151',
              }}>
                <span style={{ fontSize: 18 }}>{item.icon}</span>
                {item.text}
              </div>
            ))}
          </motion.div>
        </div>
      </AuroraBackground>

      {/* ── Features Bento Grid ── */}
      <div id="features" style={{ padding: '100px 60px', background: '#fff' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
          <motion.div initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.6 }} style={{ textAlign: 'center', marginBottom: 64 }}>
            <div style={{ fontSize: 13, fontWeight: 700, letterSpacing: 2, color: '#6366f1', textTransform: 'uppercase', marginBottom: 12 }}>核心功能</div>
            <h2 style={{ fontSize: 40, fontWeight: 800, color: '#0f172a', margin: 0, letterSpacing: '-0.5px' }}>
              一站式 AI 学习平台
            </h2>
            <p style={{ marginTop: 16, fontSize: 17, color: '#64748b', maxWidth: 500, margin: '16px auto 0' }}>
              从入门到精通，每一步都有 AI 导师陪伴
            </p>
          </motion.div>

          {/* Bento Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gridTemplateRows: 'auto auto', gap: 20 }}>
            {/* Large card */}
            <motion.div initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.5, delay: 0 }}
              style={{
                gridColumn: '1 / 2', gridRow: '1 / 3',
                borderRadius: 24, padding: 36,
                background: 'linear-gradient(145deg, rgba(99,102,241,0.06), rgba(139,92,246,0.1))',
                border: '1px solid rgba(99,102,241,0.15)',
                display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
                minHeight: 300, cursor: 'default',
                transition: 'transform 0.25s ease, box-shadow 0.25s ease',
              }}
              whileHover={{ y: -4, boxShadow: '0 16px 48px rgba(99,102,241,0.16)' }}
            >
              <div style={{ width: 56, height: 56, borderRadius: 16, background: 'linear-gradient(135deg,#6366f1,#8b5cf6)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 26, color: '#fff', boxShadow: '0 6px 20px rgba(99,102,241,0.4)', marginBottom: 24 }}>
                <RobotOutlined />
              </div>
              <div>
                <h3 style={{ fontSize: 22, fontWeight: 700, color: '#0f172a', marginBottom: 12 }}>AI 智能辅导</h3>
                <p style={{ color: '#64748b', fontSize: 15, lineHeight: 1.7 }}>基于先进大语言模型，提供个性化的实时学习指导与答疑，深度思考模式展示完整推理过程。</p>
              </div>
              <div style={{ marginTop: 24, display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {['深度思考', '流式输出', '多模型'].map(tag => (
                  <span key={tag} style={{ padding: '4px 12px', borderRadius: 99, background: 'rgba(99,102,241,0.1)', color: '#6366f1', fontSize: 12, fontWeight: 600 }}>{tag}</span>
                ))}
              </div>
            </motion.div>

            {/* Right top cards */}
            {[
              { icon: <BookOutlined />, title: '知识图谱', desc: '可视化知识结构，帮你建立完整的知识体系', grad: 'linear-gradient(135deg,#06b6d4,#10b981)', delay: 0.1 },
              { icon: <LineChartOutlined />, title: '学情分析', desc: '深度分析薄弱环节，实时追踪学习进度', grad: 'linear-gradient(135deg,#8b5cf6,#ec4899)', delay: 0.15 },
              { icon: <TeamOutlined />, title: '智能学习计划', desc: 'AI 定制专属学习路线，按节奏科学推进', grad: 'linear-gradient(135deg,#f59e0b,#ef4444)', delay: 0.2 },
              { icon: <RocketOutlined />, title: '科学复习', desc: '遗忘曲线算法驱动，高效巩固所学知识', grad: 'linear-gradient(135deg,#10b981,#06b6d4)', delay: 0.25 },
            ].map((f, i) => (
              <motion.div key={i} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.5, delay: f.delay }}
                style={{
                  borderRadius: 20, padding: '28px 28px',
                  background: '#fff', border: '1px solid #f1f5f9',
                  boxShadow: '0 2px 16px rgba(99,102,241,0.06)',
                  transition: 'all 0.25s ease', cursor: 'default',
                }}
                whileHover={{ y: -3, boxShadow: '0 10px 36px rgba(99,102,241,0.12)' }}
              >
                <div style={{ width: 44, height: 44, borderRadius: 12, background: f.grad, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 20, color: '#fff', marginBottom: 16 }}>
                  {f.icon}
                </div>
                <h3 style={{ fontSize: 16, fontWeight: 700, color: '#0f172a', marginBottom: 8 }}>{f.title}</h3>
                <p style={{ color: '#64748b', fontSize: 13.5, lineHeight: 1.6 }}>{f.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Stats ── */}
      <div style={{ padding: '80px 60px', background: 'linear-gradient(180deg, #f0f4ff 0%, #f8faff 100%)', position: 'relative', overflow: 'hidden' }}>
        <div className="aurora-orb aurora-orb-2" style={{ width: 400, height: 400, background: 'radial-gradient(circle, rgba(6,182,212,0.25), transparent)', top: '-100px', right: '-60px' }} />
        <div style={{ maxWidth: 900, margin: '0 auto', position: 'relative', zIndex: 1 }}>
          <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.6 }} style={{ textAlign: 'center', marginBottom: 56 }}>
            <h2 style={{ fontSize: 36, fontWeight: 800, color: '#0f172a' }}>已帮助无数学生突破学习瓶颈</h2>
          </motion.div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 20 }}>
            <StatCard value="10,000+" label="累计服务学生" gradient="linear-gradient(135deg,#6366f1,#8b5cf6)" delay={0} />
            <StatCard value="95%" label="用户满意度" gradient="linear-gradient(135deg,#06b6d4,#10b981)" delay={0.1} />
            <StatCard value="3.5B+" label="Token 交互量" gradient="linear-gradient(135deg,#f59e0b,#ec4899)" delay={0.2} />
            <StatCard value="50+" label="覆盖知识领域" gradient="linear-gradient(135deg,#10b981,#06b6d4)" delay={0.3} />
          </div>
        </div>
      </div>

      {/* ── Why section ── */}
      <div style={{ padding: '100px 60px', background: '#fff' }}>
        <div style={{ maxWidth: 1000, margin: '0 auto', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 80, alignItems: 'center' }}>
          <motion.div initial={{ opacity: 0, x: -24 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true }} transition={{ duration: 0.6 }}>
            <div style={{ fontSize: 13, fontWeight: 700, letterSpacing: 2, color: '#6366f1', textTransform: 'uppercase', marginBottom: 12 }}>为什么选择我们</div>
            <h2 style={{ fontSize: 36, fontWeight: 800, color: '#0f172a', marginBottom: 32, lineHeight: 1.2 }}>让 AI 成为你最好的学习伙伴</h2>
            {[
              { icon: '⚡', title: '24/7 随时在线', desc: '无论白天黑夜，AI 导师随时为你解惑' },
              { icon: '🎯', title: '个性化路径', desc: 'AI 根据掌握度智能推荐下一步学习内容' },
              { icon: '🧠', title: '科学记忆巩固', desc: '基于艾宾浩斯曲线，在最佳时机复习强化' },
              { icon: '📈', title: '可视化进度', desc: '清晰图表呈现学习数据，成就感倍增' },
            ].map((item, i) => (
              <motion.div key={i} initial={{ opacity: 0, x: -16 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true }} transition={{ duration: 0.5, delay: i * 0.1 }}
                style={{ display: 'flex', gap: 16, alignItems: 'flex-start', marginBottom: 24 }}>
                <div style={{ width: 44, height: 44, borderRadius: 12, background: 'linear-gradient(135deg,rgba(99,102,241,0.1),rgba(139,92,246,0.1))', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 20, flexShrink: 0 }}>
                  {item.icon}
                </div>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 15, color: '#0f172a', marginBottom: 4 }}>{item.title}</div>
                  <div style={{ fontSize: 14, color: '#64748b', lineHeight: 1.6 }}>{item.desc}</div>
                </div>
              </motion.div>
            ))}
          </motion.div>

          <motion.div initial={{ opacity: 0, x: 24 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true }} transition={{ duration: 0.6 }}>
            <div style={{ borderRadius: 28, overflow: 'hidden', padding: 32, background: 'linear-gradient(145deg,#6366f1,#8b5cf6)', position: 'relative', boxShadow: '0 24px 64px rgba(99,102,241,0.35)' }}>
              <div style={{ position: 'absolute', top: -30, right: -30, width: 200, height: 200, background: 'rgba(255,255,255,0.08)', borderRadius: '50%' }} />
              <div style={{ position: 'absolute', bottom: -40, left: -20, width: 180, height: 180, background: 'rgba(6,182,212,0.2)', borderRadius: '50%' }} />
              <div style={{ position: 'relative', zIndex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 28 }}>
                  <div style={{ width: 44, height: 44, borderRadius: 12, background: 'rgba(255,255,255,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <RobotOutlined style={{ color: '#fff', fontSize: 22 }} />
                  </div>
                  <div>
                    <div style={{ color: '#fff', fontWeight: 700, fontSize: 15 }}>AI Tutor</div>
                    <div style={{ color: 'rgba(255,255,255,0.6)', fontSize: 12 }}>在线 · 随时回复</div>
                  </div>
                  <div style={{ marginLeft: 'auto', width: 10, height: 10, borderRadius: '50%', background: '#4ade80', boxShadow: '0 0 8px #4ade80' }} />
                </div>
                {[
                  { role: 'user', text: '请帮我制定一个学习 Python 的计划' },
                  { role: 'ai', text: '好的！根据你的基础，我为你设计了一个 4 周渐进式学习路线，并已生成对应的知识图谱...' },
                ].map((msg, i) => (
                  <div key={i} style={{ display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start', marginBottom: 14 }}>
                    <div style={{
                      padding: '10px 16px', borderRadius: msg.role === 'user' ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
                      background: msg.role === 'user' ? 'rgba(255,255,255,0.2)' : 'rgba(255,255,255,0.9)',
                      color: msg.role === 'user' ? '#fff' : '#374151',
                      fontSize: 13.5, maxWidth: '80%', lineHeight: 1.6,
                    }}>
                      {msg.text}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        </div>
      </div>

      {/* ── Testimonials ── */}
      <div style={{ padding: '100px 60px', background: 'linear-gradient(180deg, #f8faff 0%, #fff 100%)' }}>
        <div style={{ maxWidth: 1000, margin: '0 auto' }}>
          <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} style={{ textAlign: 'center', marginBottom: 56 }}>
            <div style={{ fontSize: 13, fontWeight: 700, letterSpacing: 2, color: '#6366f1', textTransform: 'uppercase', marginBottom: 12 }}>用户评价</div>
            <h2 style={{ fontSize: 36, fontWeight: 800, color: '#0f172a' }}>他们都在用 AI Tutor 学习</h2>
          </motion.div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 24 }}>
            {testimonials.map((t, i) => (
              <motion.div key={i} initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.5, delay: i * 0.1 }}
                style={{
                  background: 'rgba(255,255,255,0.85)', backdropFilter: 'blur(16px)',
                  border: '1px solid rgba(226,232,240,0.8)', borderRadius: 20,
                  padding: 28, boxShadow: '0 4px 24px rgba(99,102,241,0.07)',
                  transition: 'all 0.25s ease',
                }}
                whileHover={{ y: -4, boxShadow: '0 12px 40px rgba(99,102,241,0.13)' }}
              >
                <div style={{ fontSize: 32, color: '#6366f1', opacity: 0.3, lineHeight: 1, marginBottom: 12 }}>"</div>
                <p style={{ fontSize: 14.5, color: '#374151', lineHeight: 1.7, marginBottom: 20 }}>{t.content}</p>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div style={{ width: 40, height: 40, borderRadius: '50%', background: t.color, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 700, fontSize: 16 }}>
                    {t.avatar}
                  </div>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: 14, color: '#0f172a' }}>{t.name}</div>
                    <div style={{ fontSize: 12, color: '#94a3b8' }}>{t.role}</div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>

      {/* ── CTA ── */}
      <div style={{ padding: '100px 60px', position: 'relative', overflow: 'hidden', background: 'linear-gradient(135deg, #4f46e5 0%, #7c3aed 50%, #0891b2 100%)' }}>
        <div className="aurora-orb" style={{ width: 500, height: 500, background: 'radial-gradient(circle, rgba(255,255,255,0.1), transparent)', top: '-150px', left: '-100px', animation: 'aurora-float-1 14s ease-in-out infinite' }} />
        <div className="aurora-orb" style={{ width: 400, height: 400, background: 'radial-gradient(circle, rgba(6,182,212,0.2), transparent)', bottom: '-100px', right: '-80px', animation: 'aurora-float-2 17s ease-in-out infinite' }} />
        <div style={{ position: 'relative', zIndex: 1, textAlign: 'center', maxWidth: 600, margin: '0 auto' }}>
          <motion.h2 initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} style={{ fontSize: 40, fontWeight: 900, color: '#fff', marginBottom: 16 }}>
            准备好开启你的学习之旅了吗？
          </motion.h2>
          <motion.p initial={{ opacity: 0, y: 16 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: 0.1 }} style={{ color: 'rgba(255,255,255,0.75)', fontSize: 18, marginBottom: 40 }}>
            免费注册，立即体验 AI 带来的个性化学习体验
          </motion.p>
          <motion.button initial={{ opacity: 0, scale: 0.95 }} whileInView={{ opacity: 1, scale: 1 }} viewport={{ once: true }} transition={{ delay: 0.2 }}
            onClick={() => navigate('/register')}
            style={{
              padding: '16px 48px', borderRadius: 14, border: 'none',
              background: '#fff', color: '#6366f1', fontSize: 18, fontWeight: 700,
              cursor: 'pointer', boxShadow: '0 8px 32px rgba(0,0,0,0.2)',
              transition: 'all 0.2s',
            }}
            onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-3px)'; e.currentTarget.style.boxShadow = '0 14px 40px rgba(0,0,0,0.28)' }}
            onMouseLeave={e => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow = '0 8px 32px rgba(0,0,0,0.2)' }}
          >
            立即免费注册 <ArrowRightOutlined />
          </motion.button>
        </div>
      </div>

      {/* ── Footer ── */}
      <footer style={{ padding: '32px 60px', background: '#0f172a', color: 'rgba(255,255,255,0.5)', textAlign: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, marginBottom: 12 }}>
          <div style={{ width: 28, height: 28, borderRadius: 8, background: 'linear-gradient(135deg,#6366f1,#8b5cf6)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <RobotOutlined style={{ color: '#fff', fontSize: 14 }} />
          </div>
          <span style={{ color: '#fff', fontWeight: 700, fontSize: 16 }}>AI Tutor</span>
        </div>
        <div style={{ fontSize: 13 }}>© 2025 AI Tutor. All rights reserved.</div>
      </footer>
    </div>
  )
}

export default LandingPage
