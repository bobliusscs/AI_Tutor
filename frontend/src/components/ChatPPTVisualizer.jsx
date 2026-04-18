import { useState, useEffect, useCallback, useRef } from 'react'
import { Tag, Tooltip, message } from 'antd'
import {
  LeftOutlined,
  RightOutlined,
  BookOutlined,
  CodeOutlined,
  EditOutlined,
  CheckCircleOutlined,
  PlayCircleOutlined,
  FileTextOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  AppstoreOutlined,
  BulbOutlined,
  SwapOutlined,
  ThunderboltOutlined,
  TrophyOutlined,
  RocketOutlined,
  SafetyOutlined,
  LinkOutlined,
  AlertOutlined,
  CheckOutlined,
  StarOutlined,
  DownloadOutlined,
  ExportOutlined
} from '@ant-design/icons'
import { motion, AnimatePresence } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'

// ─────────────────────────────────────────────────────────────────────────────
// 常量定义
// ─────────────────────────────────────────────────────────────────────────────

const SLIDE_CONFIG = {
  cover:     { icon: BookOutlined,      label: '封面',   color: '#6366f1', gradient: 'linear-gradient(135deg, #4F46E5 0%, #7C3AED 50%, #9333EA 100%)' },
  intro:     { icon: RocketOutlined,    label: '导入',   color: '#f59e0b', gradient: 'linear-gradient(135deg, #F59E0B 0%, #EF4444 100%)' },
  concept:   { icon: BulbOutlined,      label: '概念',   color: '#3b82f6', gradient: 'linear-gradient(135deg, #3B82F6 0%, #6366F1 100%)' },
  content:   { icon: FileTextOutlined,  label: '讲解',   color: '#0ea5e9', gradient: 'linear-gradient(135deg, #0EA5E9 0%, #3B82F6 100%)' },
  example:   { icon: PlayCircleOutlined,label: '案例',   color: '#10b981', gradient: 'linear-gradient(135deg, #10B981 0%, #059669 100%)' },
  comparison:{ icon: SwapOutlined,      label: '对比',   color: '#8b5cf6', gradient: 'linear-gradient(135deg, #8B5CF6 0%, #6366F1 100%)' },
  exercise:  { icon: EditOutlined,      label: '练习',   color: '#ef4444', gradient: 'linear-gradient(135deg, #EF4444 0%, #F59E0B 100%)' },
  summary:   { icon: CheckCircleOutlined, label: '总结', color: '#06b6d4', gradient: 'linear-gradient(135deg, #06B6D4 0%, #3B82F6 100%)' },
  ending:    { icon: TrophyOutlined,    label: '结束',   color: '#f59e0b', gradient: 'linear-gradient(135deg, #F59E0B 0%, #EF4444 50%, #EC4899 100%)' },
  guide:     { icon: ThunderboltOutlined, label: '导览', color: '#8b5cf6', gradient: 'linear-gradient(135deg, #8B5CF6 0%, #EC4899 100%)' },
}

const ICON_MAP = {
  lightbulb: BulbOutlined,
  cog: ThunderboltOutlined,
  link: LinkOutlined,
  shield: SafetyOutlined,
  trend: RocketOutlined,
  star: StarOutlined,
  alert: AlertOutlined,
  check: CheckOutlined,
}

const slideVariants = {
  enter: (direction) => ({
    x: direction > 0 ? 600 : -600,
    opacity: 0,
    scale: 0.92,
    rotateY: direction > 0 ? 5 : -5,
  }),
  center: { x: 0, opacity: 1, scale: 1, rotateY: 0 },
  exit: (direction) => ({
    x: direction < 0 ? 600 : -600,
    opacity: 0,
    scale: 0.92,
    rotateY: direction < 0 ? 5 : -5,
  })
}

// ─────────────────────────────────────────────────────────────────────────────
// 工具函数
// ─────────────────────────────────────────────────────────────────────────────

function parseSlideContent(slide) {
  const raw = slide.content
  if (raw && typeof raw === 'object') return raw
  if (typeof raw === 'string' && raw.trim()) return { text: raw }
  return {}
}

function getSlideTypeConfig(type) {
  return SLIDE_CONFIG[type] || SLIDE_CONFIG.content
}

// ─────────────────────────────────────────────────────────────────────────────
// 幻灯片内容渲染器 - 视觉优先，文字极简
// ─────────────────────────────────────────────────────────────────────────────

/** Markdown精简渲染 */
function MarkdownText({ content }) {
  if (!content) return null
  const components = {
    code({ node, inline, className, children, ...props }) {
      const match = /language-(\w+)/.exec(className || '')
      const codeStr = String(children).replace(/\n$/, '')
      if (!inline && match) {
        return (
          <SyntaxHighlighter style={oneDark} language={match[1]} PreTag="div"
            customStyle={{ margin: '6px 0', borderRadius: 8, fontSize: 12 }} {...props}>
            {codeStr}
          </SyntaxHighlighter>
        )
      }
      return <code style={{ background: 'rgba(99,102,241,0.12)', padding: '1px 5px', borderRadius: 4, fontSize: '0.85em', color: '#6366f1' }} {...props}>{children}</code>
    },
    strong: ({ children }) => <strong style={{ color: '#4F46E5', fontWeight: 700 }}>{children}</strong>,
    p: ({ children }) => <span style={{ lineHeight: 1.7 }}>{children}</span>,
    ul: ({ children }) => <ul style={{ paddingLeft: 16, margin: 0 }}>{children}</ul>,
    ol: ({ children }) => <ol style={{ paddingLeft: 16, margin: 0 }}>{children}</ol>,
    li: ({ children }) => <li style={{ margin: '2px 0', lineHeight: 1.6 }}>{children}</li>,
  }
  return <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>{content}</ReactMarkdown>
}

/** 封面页 - 大气渐变+居中标题+丰富装饰 */
function CoverSlideRenderer({ data, slideConfig }) {
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', padding: '36px 48px', background: slideConfig.gradient, color: '#fff', position: 'relative', overflow: 'hidden' }}>
      {/* 装饰几何元素 */}
      <div style={{ position: 'absolute', top: -100, right: -100, width: 300, height: 300, borderRadius: '50%', background: 'rgba(255,255,255,0.06)' }} />
      <div style={{ position: 'absolute', bottom: -80, left: -80, width: 240, height: 240, borderRadius: '50%', background: 'rgba(255,255,255,0.04)' }} />
      <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', width: 500, height: 500, borderRadius: '50%', background: 'rgba(255,255,255,0.02)' }} />
      {/* 装饰菱形 */}
      <div style={{ position: 'absolute', top: 60, right: 80, width: 40, height: 40, border: '2px solid rgba(255,255,255,0.1)', transform: 'rotate(45deg)' }} />
      <div style={{ position: 'absolute', bottom: 80, left: 100, width: 24, height: 24, border: '2px solid rgba(255,255,255,0.08)', transform: 'rotate(45deg)' }} />
      {/* 装饰圆点 */}
      <div style={{ position: 'absolute', top: 120, left: 60, width: 8, height: 8, borderRadius: '50%', background: 'rgba(255,255,255,0.15)' }} />
      <div style={{ position: 'absolute', top: 160, left: 90, width: 5, height: 5, borderRadius: '50%', background: 'rgba(255,255,255,0.1)' }} />
      <div style={{ position: 'absolute', bottom: 140, right: 120, width: 10, height: 10, borderRadius: '50%', background: 'rgba(255,255,255,0.12)' }} />
      {/* 横线装饰 */}
      <div style={{ position: 'absolute', top: 40, left: 40, width: 60, height: 2, background: 'rgba(255,255,255,0.1)' }} />
      <div style={{ position: 'absolute', bottom: 40, right: 40, width: 80, height: 2, background: 'rgba(255,255,255,0.08)' }} />
      
      <div style={{ position: 'relative', zIndex: 1, textAlign: 'center', maxWidth: 680 }}>
        {data.subtitle && (
          <div style={{ fontSize: 13, letterSpacing: 6, textTransform: 'uppercase', opacity: 0.7, marginBottom: 20, fontWeight: 500 }}>
            {data.subtitle}
          </div>
        )}
        <h1 style={{ fontSize: 36, fontWeight: 800, margin: 0, lineHeight: 1.25, textShadow: '0 4px 20px rgba(0,0,0,0.15)', letterSpacing: 1 }}>
          {data.title || ''}
        </h1>
        {/* 分割线 */}
        <div style={{ width: 60, height: 3, background: 'rgba(255,255,255,0.5)', margin: '24px auto', borderRadius: 2 }} />
        
        {data.objectives && data.objectives.length > 0 && (
          <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 10, alignItems: 'center' }}>
            {data.objectives.map((obj, idx) => (
              <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: 14, background: 'rgba(255,255,255,0.1)', padding: '10px 22px', borderRadius: 50, backdropFilter: 'blur(8px)', border: '1px solid rgba(255,255,255,0.1)' }}>
                <span style={{ width: 26, height: 26, borderRadius: '50%', background: 'rgba(255,255,255,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 700, flexShrink: 0 }}>
                  {idx + 1}
                </span>
                <span style={{ fontSize: 14, fontWeight: 500 }}>{obj}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

/** 导入页 - 场景+问题，视觉丰富 */
function IntroSlideRenderer({ data }) {
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', padding: '28px 40px', gap: 20, position: 'relative' }}>
      {/* 背景装饰 */}
      <div style={{ position: 'absolute', top: -40, right: -40, width: 180, height: 180, borderRadius: '50%', background: 'linear-gradient(135deg, #FEF3C7, #FDE68A)', opacity: 0.3 }} />
      <div style={{ position: 'absolute', bottom: -30, left: -30, width: 120, height: 120, borderRadius: '50%', background: 'linear-gradient(135deg, #EDE9FE, #DDD6FE)', opacity: 0.3 }} />
      <div style={{ position: 'absolute', top: 20, right: 30, width: 30, height: 30, border: '2px solid #FDE68A', transform: 'rotate(45deg)', opacity: 0.4 }} />
      
      {data.scene && (
        <div style={{ background: 'linear-gradient(135deg, #FFFBEB, #FEF3C7)', borderRadius: 20, padding: '26px 34px', border: '1px solid #FDE68A', textAlign: 'center', width: '100%', maxWidth: 580, position: 'relative', boxShadow: '0 8px 32px rgba(245,158,11,0.12)' }}>
          <div style={{ position: 'absolute', top: -10, left: 24, background: '#F59E0B', color: '#fff', fontSize: 10, fontWeight: 700, padding: '3px 12px', borderRadius: 10, letterSpacing: 1 }}>场景</div>
          <div style={{ fontSize: 18, color: '#92400E', fontWeight: 600, lineHeight: 1.5 }}>{data.scene}</div>
        </div>
      )}
      
      {data.question && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, background: 'linear-gradient(135deg, #F5F3FF, #EDE9FE)', borderRadius: 20, padding: '22px 30px', border: '1px solid #DDD6FE', boxShadow: '0 8px 32px rgba(139,92,246,0.1)', width: '100%', maxWidth: 580 }}>
          <div style={{ width: 44, height: 44, borderRadius: 14, background: 'linear-gradient(135deg, #7C3AED, #6366F1)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, boxShadow: '0 4px 12px rgba(124,58,237,0.3)' }}>
            <BulbOutlined style={{ fontSize: 22, color: '#fff' }} />
          </div>
          <span style={{ fontSize: 20, color: '#4C1D95', fontWeight: 700 }}>{data.question}</span>
        </div>
      )}
      
      {data.answer_hint && (
        <div style={{ background: 'linear-gradient(135deg, #F0FDF4, #DCFCE7)', borderRadius: 50, padding: '10px 24px', border: '1px solid #86EFAC', fontSize: 14, color: '#166534', fontWeight: 600, boxShadow: '0 4px 16px rgba(16,185,129,0.1)' }}>
          💡 {data.answer_hint}
        </div>
      )}
    </div>
  )
}

/** 概念页 - 大定义框+属性卡片+图示区域 */
function ConceptSlideRenderer({ data }) {
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: '20px 36px', gap: 14, position: 'relative' }}>
      {/* 背景装饰 */}
      <div style={{ position: 'absolute', top: -20, right: -20, width: 140, height: 140, borderRadius: '50%', background: 'linear-gradient(135deg, #EEF2FF, #E0E7FF)', opacity: 0.5 }} />
      
      {data.definition && (
        <div style={{ background: 'linear-gradient(135deg, #EEF2FF, #E0E7FF)', borderRadius: 20, padding: '24px 30px', borderLeft: '6px solid #4F46E5', textAlign: 'center', position: 'relative', boxShadow: '0 8px 32px rgba(79,70,229,0.1)' }}>
          <div style={{ position: 'absolute', top: -8, right: 20, background: '#4F46E5', color: '#fff', fontSize: 9, fontWeight: 700, padding: '2px 10px', borderRadius: 8, letterSpacing: 1 }}>定义</div>
          <div style={{ fontSize: 20, color: '#312E81', fontWeight: 700, lineHeight: 1.6 }}>
            <MarkdownText content={data.definition} />
          </div>
        </div>
      )}
      
      {data.key_attributes && data.key_attributes.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: `repeat(${Math.min(data.key_attributes.length, 3)}, 1fr)`, gap: 14 }}>
          {data.key_attributes.map((attr, idx) => {
            const colors = ['#6366F1', '#3B82F6', '#10B981', '#F59E0B']
            const color = colors[idx % colors.length]
            return (
              <div key={idx} style={{ background: '#fff', borderRadius: 16, padding: '20px 18px', border: `2px solid ${color}20`, boxShadow: `0 4px 16px ${color}08`, textAlign: 'center', position: 'relative', overflow: 'hidden' }}>
                <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 3, background: `linear-gradient(90deg, ${color}, ${color}60)` }} />
                <div style={{ fontSize: 13, fontWeight: 700, color, marginBottom: 6 }}>{attr.label}</div>
                <div style={{ fontSize: 15, color: '#334155', fontWeight: 500 }}>{attr.value}</div>
              </div>
            )
          })}
        </div>
      )}
      
      {data.diagram_hint && (
        <div style={{ background: 'linear-gradient(135deg, #F5F3FF, #EDE9FE)', borderRadius: 14, padding: '12px 20px', border: '1px dashed #C4B5FD', textAlign: 'center' }}>
          <span style={{ fontSize: 12, color: '#6D28D9', fontWeight: 600 }}>📊 {data.diagram_hint}</span>
        </div>
      )}
    </div>
  )
}

/** 内容讲解页 - 大图标要点+视觉装饰 */
function ContentSlideRenderer({ data }) {
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: '20px 36px', gap: 12, position: 'relative' }}>
      {/* 背景装饰 */}
      <div style={{ position: 'absolute', bottom: -20, right: -20, width: 120, height: 120, borderRadius: '50%', background: 'linear-gradient(135deg, #DBEAFE, #BFDBFE)', opacity: 0.4 }} />
      
      {data.main_idea && (
        <div style={{ background: 'linear-gradient(135deg, #EFF6FF, #DBEAFE)', borderRadius: 16, padding: '16px 24px', borderLeft: '5px solid #3B82F6', textAlign: 'center', position: 'relative', boxShadow: '0 6px 24px rgba(59,130,246,0.1)' }}>
          <div style={{ position: 'absolute', top: -8, left: 20, background: '#3B82F6', color: '#fff', fontSize: 9, fontWeight: 700, padding: '2px 10px', borderRadius: 8 }}>核心</div>
          <span style={{ fontSize: 18, color: '#1E40AF', fontWeight: 700 }}>{data.main_idea}</span>
        </div>
      )}
      
      {data.points && data.points.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {data.points.map((point, idx) => {
            const IconComp = ICON_MAP[point.icon] || StarOutlined
            const colors = ['#6366F1', '#3B82F6', '#10B981', '#F59E0B', '#EF4444']
            const color = colors[idx % colors.length]
            return (
              <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: 16, background: '#fff', borderRadius: 16, padding: '16px 20px', border: `1px solid ${color}15`, boxShadow: `0 4px 16px ${color}06`, position: 'relative', overflow: 'hidden' }}>
                <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: 4, background: `linear-gradient(180deg, ${color}, ${color}60)` }} />
                <div style={{ width: 48, height: 48, borderRadius: 14, background: `${color}10`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                  <IconComp style={{ color, fontSize: 22 }} />
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 16, fontWeight: 700, color: '#1E293B', marginBottom: 2 }}>{point.title}</div>
                  {point.detail && <div style={{ fontSize: 14, color: '#64748B' }}><MarkdownText content={point.detail} /></div>}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

/** 案例页 - 步骤流程+视觉增强 */
function ExampleSlideRenderer({ data }) {
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: '18px 36px', gap: 10, position: 'relative' }}>
      {/* 背景装饰 */}
      <div style={{ position: 'absolute', top: -10, left: -10, width: 100, height: 100, borderRadius: '50%', background: 'linear-gradient(135deg, #F0FDF4, #DCFCE7)', opacity: 0.4 }} />
      
      {data.case_title && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ width: 44, height: 44, borderRadius: 14, background: 'linear-gradient(135deg, #10B981, #059669)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 4px 12px rgba(16,185,129,0.3)' }}>
            <PlayCircleOutlined style={{ color: '#fff', fontSize: 20 }} />
          </div>
          <span style={{ fontSize: 20, fontWeight: 700, color: '#065F46' }}>{data.case_title}</span>
        </div>
      )}
      
      {data.background && (
        <div style={{ background: 'linear-gradient(135deg, #F0FDF4, #DCFCE7)', borderRadius: 12, padding: '12px 18px', fontSize: 14, color: '#166534', border: '1px solid #BBF7D0', boxShadow: '0 4px 12px rgba(16,185,129,0.08)' }}>
          📋 {data.background}
        </div>
      )}
      
      {data.steps && data.steps.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, position: 'relative' }}>
          {/* 连接线 */}
          {data.steps.length > 1 && (
            <div style={{ position: 'absolute', left: 17, top: 20, bottom: 20, width: 2, background: 'linear-gradient(180deg, #6366F1, #3B82F6, #10B981)', borderRadius: 1, opacity: 0.3 }} />
          )}
          {data.steps.map((step, idx) => {
            const colors = ['#6366F1', '#3B82F6', '#10B981', '#F59E0B', '#EF4444']
            const color = colors[idx % colors.length]
            return (
              <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: 12, position: 'relative', zIndex: 1 }}>
                <div style={{ width: 36, height: 36, borderRadius: '50%', background: `linear-gradient(135deg, ${color}, ${color}CC)`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, color: '#fff', fontSize: 14, fontWeight: 700, boxShadow: `0 4px 12px ${color}30` }}>
                  {idx + 1}
                </div>
                <div style={{ flex: 1, background: '#FAFAFA', borderRadius: 12, padding: '12px 16px', border: `1px solid #F1F5F9`, borderLeft: `3px solid ${color}`, display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{ fontSize: 13, fontWeight: 700, color, flexShrink: 0 }}>{step.label}</span>
                  <span style={{ fontSize: 14, color: '#475569' }}>{step.content}</span>
                </div>
              </div>
            )
          })}
        </div>
      )}
      
      {data.insight && (
        <div style={{ background: 'linear-gradient(135deg, #FFFBEB, #FEF3C7)', borderRadius: 12, padding: '12px 18px', border: '1px solid #FDE68A', boxShadow: '0 4px 12px rgba(245,158,11,0.08)' }}>
          <span style={{ fontSize: 12, fontWeight: 700, color: '#92400E' }}>💡 </span>
          <span style={{ fontSize: 14, color: '#78350F', fontWeight: 600 }}>{data.insight}</span>
        </div>
      )}
    </div>
  )
}

/** 对比页 - 双栏大卡片+视觉增强 */
function ComparisonSlideRenderer({ data }) {
  const colors = ['#6366F1', '#EF4444']
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: '18px 36px', gap: 12, position: 'relative' }}>
      {/* 背景VS标记 */}
      <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', width: 50, height: 50, borderRadius: '50%', background: 'linear-gradient(135deg, #F5F3FF, #EDE9FE)', display: 'flex', alignItems: 'center', justifyContent: 'center', border: '2px solid #DDD6FE', zIndex: 5, boxShadow: '0 4px 16px rgba(139,92,246,0.15)' }}>
        <span style={{ fontSize: 14, fontWeight: 800, color: '#7C3AED' }}>VS</span>
      </div>
      
      {data.items && data.items.length >= 2 && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
          {data.items.map((item, idx) => {
            const color = colors[idx % colors.length]
            return (
              <div key={idx} style={{ background: '#fff', borderRadius: 18, padding: '22px 20px', border: `2px solid ${color}25`, boxShadow: `0 6px 24px ${color}10`, textAlign: 'center', position: 'relative', overflow: 'hidden' }}>
                <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 4, background: `linear-gradient(90deg, ${color}, ${color}60)` }} />
                <div style={{ width: 12, height: 12, borderRadius: '50%', background: color, margin: '0 auto 12px', boxShadow: `0 2px 8px ${color}40` }} />
                <div style={{ fontSize: 20, fontWeight: 700, color, marginBottom: 14 }}>{item.name}</div>
                {item.features && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {item.features.map((f, fi) => (
                      <div key={fi} style={{ padding: '8px 14px', background: `${color}06`, borderRadius: 10, fontSize: 14, color: '#475569', fontWeight: 500, border: `1px solid ${color}10` }}>
                        ✓ {f}
                      </div>
                    ))}
                  </div>
                )}
                {item.example && (
                  <div style={{ marginTop: 12, padding: '8px 14px', background: `${color}04`, borderRadius: 8, fontSize: 12, color: '#64748B', border: `1px dashed ${color}20` }}>
                    例：{item.example}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
      
      {data.key_difference && (
        <div style={{ background: 'linear-gradient(135deg, #F5F3FF, #EDE9FE)', borderRadius: 14, padding: '14px 24px', border: '1px solid #DDD6FE', textAlign: 'center', boxShadow: '0 4px 16px rgba(139,92,246,0.08)' }}>
          <span style={{ fontSize: 12, fontWeight: 700, color: '#5B21B6' }}>核心区别 </span>
          <span style={{ fontSize: 16, color: '#4C1D95', fontWeight: 700 }}>{data.key_difference}</span>
        </div>
      )}
    </div>
  )
}

/** 总结页 - 要点+关键词标签+视觉增强 */
function SummarySlideRenderer({ data }) {
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: '20px 36px', gap: 10, position: 'relative' }}>
      {/* 背景装饰 */}
      <div style={{ position: 'absolute', top: -15, right: -15, width: 120, height: 120, borderRadius: '50%', background: 'linear-gradient(135deg, #CFFAFE, #A5F3FC)', opacity: 0.3 }} />
      <div style={{ position: 'absolute', bottom: -10, left: -10, width: 80, height: 80, borderRadius: '50%', background: 'linear-gradient(135deg, #E0E7FF, #C7D2FE)', opacity: 0.3 }} />
      
      {data.key_takeaways && data.key_takeaways.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {data.key_takeaways.map((item, idx) => {
            const colors = ['#6366F1', '#3B82F6', '#10B981', '#F59E0B', '#EF4444']
            const color = colors[idx % colors.length]
            return (
              <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: 14, background: '#fff', borderRadius: 14, padding: '14px 20px', border: `1px solid ${color}15`, boxShadow: `0 4px 16px ${color}06`, position: 'relative', overflow: 'hidden' }}>
                <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: 4, background: `linear-gradient(180deg, ${color}, ${color}60)` }} />
                <div style={{ width: 40, height: 40, borderRadius: 12, background: `${color}10`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                  <CheckCircleOutlined style={{ color, fontSize: 20 }} />
                </div>
                <span style={{ flex: 1, fontSize: 16, color: '#1E293B', fontWeight: 600 }}>{item.point}</span>
                {item.keyword && (
                  <span style={{ background: `${color}10`, color, padding: '6px 14px', borderRadius: 8, fontSize: 13, fontWeight: 700, whiteSpace: 'nowrap', border: `1px solid ${color}20` }}>
                    {item.keyword}
                  </span>
                )}
              </div>
            )
          })}
        </div>
      )}
      {data.mind_map_hint && (
        <div style={{ padding: '10px 18px', background: 'linear-gradient(135deg, #F0F9FF, #E0F2FE)', borderRadius: 10, border: '1px dashed #7DD3FC', fontSize: 12, color: '#0369A1', textAlign: 'center', boxShadow: '0 4px 12px rgba(14,165,233,0.06)' }}>
          🧠 {data.mind_map_hint}
        </div>
      )}
    </div>
  )
}

/** 结束页 - 渐变+居中+丰富装饰 */
function EndingSlideRenderer({ data, slideConfig }) {
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', padding: '36px 48px', background: slideConfig.gradient, color: '#fff', position: 'relative', overflow: 'hidden' }}>
      {/* 装饰元素 */}
      <div style={{ position: 'absolute', top: -50, left: -50, width: 200, height: 200, borderRadius: '50%', background: 'rgba(255,255,255,0.06)' }} />
      <div style={{ position: 'absolute', bottom: -40, right: -40, width: 160, height: 160, borderRadius: '50%', background: 'rgba(255,255,255,0.04)' }} />
      <div style={{ position: 'absolute', top: 40, right: 60, width: 30, height: 30, border: '2px solid rgba(255,255,255,0.1)', transform: 'rotate(45deg)' }} />
      <div style={{ position: 'absolute', bottom: 60, left: 80, width: 8, height: 8, borderRadius: '50%', background: 'rgba(255,255,255,0.15)' }} />
      <div style={{ position: 'absolute', top: 80, left: 40, width: 5, height: 5, borderRadius: '50%', background: 'rgba(255,255,255,0.1)' }} />
      {/* 横线装饰 */}
      <div style={{ position: 'absolute', bottom: 50, right: 50, width: 50, height: 2, background: 'rgba(255,255,255,0.1)' }} />
      
      <div style={{ position: 'relative', zIndex: 1, textAlign: 'center', maxWidth: 500 }}>
        <div style={{ width: 64, height: 64, borderRadius: '50%', background: 'rgba(255,255,255,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px' }}>
          <TrophyOutlined style={{ fontSize: 36, opacity: 0.9 }} />
        </div>
        {data.message && <h2 style={{ fontSize: 28, fontWeight: 700, margin: '0 0 24px', textShadow: '0 2px 12px rgba(0,0,0,0.15)' }}>{data.message}</h2>}
        <div style={{ width: 40, height: 3, background: 'rgba(255,255,255,0.3)', margin: '0 auto 24px', borderRadius: 2 }} />
        {data.next_topic && (
          <div style={{ background: 'rgba(255,255,255,0.1)', borderRadius: 14, padding: '16px 24px', marginBottom: 14, backdropFilter: 'blur(4px)', border: '1px solid rgba(255,255,255,0.1)' }}>
            <div style={{ fontSize: 11, opacity: 0.6, marginBottom: 4, letterSpacing: 1 }}>下节预告</div>
            <div style={{ fontSize: 16, fontWeight: 600 }}>{data.next_topic}</div>
          </div>
        )}
        {data.review_tip && (
          <div style={{ fontSize: 14, opacity: 0.7, fontStyle: 'italic' }}>📖 {data.review_tip}</div>
        )}
      </div>
    </div>
  )
}

/** 练习题渲染 - 视觉增强 */
function ExerciseSlideRenderer({ data, questions }) {
  // 统一字段适配：题目内容
  const getQuestionText = (q) => q.question_text || q.stem || q.question || q.knowledge_point_name || ''
  // 统一字段适配：选项处理
  const getOptionText = (opt) => {
    if (typeof opt === 'string') return opt.replace(/^[A-D]\.\s*/, '')
    if (typeof opt === 'object' && opt !== null) return opt.text || opt.label || String(opt)
    return String(opt)
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: '18px 36px', position: 'relative' }}>
      {/* 背景装饰 */}
      <div style={{ position: 'absolute', top: -15, right: -15, width: 100, height: 100, borderRadius: '50%', background: 'linear-gradient(135deg, #FEE2E2, #FECACA)', opacity: 0.3 }} />
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {questions && questions.length > 0 ? questions.map((q, idx) => (
          <div key={idx} style={{ background: '#fff', borderRadius: 16, padding: '16px 20px', border: '1px solid #E2E8F0', boxShadow: '0 4px 16px rgba(0,0,0,0.04)', position: 'relative', overflow: 'hidden' }}>
            <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 3, background: `linear-gradient(90deg, ${['#EF4444', '#F59E0B', '#10B981'][idx % 3]}, ${['#EF4444', '#F59E0B', '#10B981'][idx % 3]}60)` }} />
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
              <span style={{ width: 28, height: 28, borderRadius: '50%', background: `linear-gradient(135deg, ${['#EF4444', '#F59E0B', '#10B981'][idx % 3]}, ${['#F97316', '#EAB308', '#059669'][idx % 3]})`, color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 700, flexShrink: 0, boxShadow: `0 2px 8px ${['#EF4444', '#F59E0B', '#10B981'][idx % 3]}30` }}>
                {idx + 1}
              </span>
              <span style={{ fontWeight: 600, fontSize: 15, color: '#1E293B', flex: 1 }}>{getQuestionText(q)}</span>
            </div>
            {q.options && (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, paddingLeft: 38 }}>
                {q.options.map((opt, oi) => (
                  <div key={oi} style={{ padding: '10px 14px', background: 'linear-gradient(135deg, #F8FAFC, #F1F5F9)', borderRadius: 10, border: '1px solid #E2E8F0', fontSize: 13, color: '#475569', fontWeight: 500 }}>
                    <span style={{ fontWeight: 700, color: '#6366f1', marginRight: 6 }}>{String.fromCharCode(65 + oi)}.</span>
                    {getOptionText(opt)}
                  </div>
                ))}
              </div>
            )}
          </div>
        )) : (
          <div style={{ textAlign: 'center', color: '#94A3B8', padding: 40 }}>
            <EditOutlined style={{ fontSize: 36, marginBottom: 12 }} />
            <div>练习题加载中...</div>
          </div>
        )}
      </div>
    </div>
  )
}

/** 通用回退渲染器 */
function FallbackSlideRenderer({ data }) {
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: '32px 44px', overflowY: 'auto' }}>
      <MarkdownText content={data.text || ''} />
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// 主幻灯片渲染分发器
// ─────────────────────────────────────────────────────────────────────────────

function SlideRenderer({ slide }) {
  const content = parseSlideContent(slide)
  const type = slide.type || 'content'
  const slideConfig = getSlideTypeConfig(type)
  const questions = slide.questions || content?.questions

  if (type === 'cover') return <CoverSlideRenderer data={content} slideConfig={slideConfig} />
  if (type === 'ending') return <EndingSlideRenderer data={content} slideConfig={slideConfig} />

  switch (type) {
    case 'intro':
      return <IntroSlideRenderer data={content} />
    case 'concept':
      return <ConceptSlideRenderer data={content} />
    case 'content':
      if (content.points || content.main_idea) return <ContentSlideRenderer data={content} />
      break
    case 'example':
      if (content.steps || content.case_title) return <ExampleSlideRenderer data={content} />
      break
    case 'comparison':
      if (content.items) return <ComparisonSlideRenderer data={content} />
      break
    case 'exercise':
      return <ExerciseSlideRenderer data={content} questions={questions} />
    case 'summary':
      if (content.key_takeaways) return <SummarySlideRenderer data={content} />
      break
  }

  return <FallbackSlideRenderer data={content} />
}

// ─────────────────────────────────────────────────────────────────────────────
// PPT导出功能
// ─────────────────────────────────────────────────────────────────────────────

/**
 * 将hex颜色与白色混合，生成pptxgenjs兼容的6位hex颜色
 * pptxgenjs不支持8位hex（如"6366F120"），需要预混合
 * @param {string} hex6 - 6位hex颜色（如"6366F1"）
 * @param {number} opacity - 不透明度 0~1（如0.12表示12.5%不透明）
 * @returns {string} 混合后的6位hex颜色
 */
function blendColor(hex6, opacity) {
  if (!hex6 || hex6.length < 6) return 'F8FAFC'
  const r = parseInt(hex6.slice(0, 2), 16)
  const g = parseInt(hex6.slice(2, 4), 16)
  const b = parseInt(hex6.slice(4, 6), 16)
  const nr = Math.round(r * opacity + 255 * (1 - opacity))
  const ng = Math.round(g * opacity + 255 * (1 - opacity))
  const nb = Math.round(b * opacity + 255 * (1 - opacity))
  return nr.toString(16).padStart(2, '0').toUpperCase()
    + ng.toString(16).padStart(2, '0').toUpperCase()
    + nb.toString(16).padStart(2, '0').toUpperCase()
}

/**
 * 将CSS 8位hex颜色（如"6366F120"）转为pptxgenjs兼容格式
 * 返回 {color, transparency} 或纯6位hex
 */
function pptxAlphaColor(cssHex8) {
  const hex6 = cssHex8.slice(0, 6)
  const alphaHex = cssHex8.slice(6, 8)
  if (!alphaHex) return hex6
  const alpha = parseInt(alphaHex, 16) / 255
  const transparency = Math.round((1 - alpha) * 100)
  return { color: hex6, transparency }
}

async function exportToPPTX(pptData) {
  const PptxGenJS = (await import('pptxgenjs')).default
  const { slides, ppt_type, chapter_title, section_title } = pptData
  const title = ppt_type === 'section' ? section_title : chapter_title

  const pptx = new PptxGenJS()
  pptx.layout = 'LAYOUT_WIDE'
  pptx.author = 'MindGuide AI Tutor'
  pptx.subject = title || '教学课件'

  const themeColors = {
    primary: '4F46E5',
    accent: 'F59E0B',
    dark: '1E293B',
    light: 'F8FAFC',
    white: 'FFFFFF',
  }

  slides?.forEach((slide) => {
    const content = parseSlideContent(slide)
    const type = slide.type || 'content'
    const config = getSlideTypeConfig(type)
    const sl = pptx.addSlide()

    // 公共样式
    const fontColor = '334155'

    // --- cover ---
    if (type === 'cover') {
      sl.background = { fill: '4F46E5' }
      // 装饰圆
      sl.addShape(pptx.ShapeType.ellipse, { x: 8.5, y: -0.8, w: 3, h: 3, fill: { color: '7C3AED', transparency: 80 } })
      sl.addShape(pptx.ShapeType.ellipse, { x: -0.5, y: 4.2, w: 2.4, h: 2.4, fill: { color: '7C3AED', transparency: 85 } })
      sl.addShape(pptx.ShapeType.ellipse, { x: 5, y: 1.5, w: 5, h: 5, fill: { color: '6366F1', transparency: 90 } })
      // 装饰菱形
      sl.addShape(pptx.ShapeType.rect, { x: 11, y: 0.8, w: 0.4, h: 0.4, fill: { color: 'FFFFFF', transparency: 88 }, rotate: 45 })
      sl.addShape(pptx.ShapeType.rect, { x: 1.5, y: 5.5, w: 0.25, h: 0.25, fill: { color: 'FFFFFF', transparency: 90 }, rotate: 45 })
      // 装饰圆点
      sl.addShape(pptx.ShapeType.ellipse, { x: 1.2, y: 1.2, w: 0.08, h: 0.08, fill: { color: 'FFFFFF', transparency: 80 } })
      sl.addShape(pptx.ShapeType.ellipse, { x: 10.5, y: 5, w: 0.1, h: 0.1, fill: { color: 'FFFFFF', transparency: 85 } })

      if (content.subtitle) {
        sl.addText(content.subtitle, { x: 0.8, y: 1.2, w: 11.4, h: 0.5, fontSize: 12, color: 'C4B5FD', align: 'center', letterSpacing: 5 })
      }
      sl.addText(content.title || slide.title || '', { x: 0.8, y: 1.8, w: 11.4, h: 1.5, fontSize: 32, color: 'FFFFFF', align: 'center', bold: true })
      // 分割线
      sl.addShape(pptx.ShapeType.rect, { x: 5.9, y: 3.4, w: 1.5, h: 0.04, fill: { color: 'FFFFFF', transparency: 50 } })
      
      if (content.objectives?.length) {
        content.objectives.forEach((obj, idx) => {
          sl.addText(`${idx + 1}  ${obj}`, {
            x: 3, y: 3.8 + idx * 0.55, w: 7, h: 0.45,
            fontSize: 14, color: 'E0E7FF', fill: { color: '6366F1', transparency: 70 },
            rectRadius: 0.2, align: 'center',
          })
        })
      }
      // 添加备注
      if (slide.notes) sl.addNotes(slide.notes)
      return
    }

    // --- ending ---
    if (type === 'ending') {
      sl.background = { fill: 'F59E0B' }
      sl.addShape(pptx.ShapeType.ellipse, { x: -0.5, y: -0.5, w: 2, h: 2, fill: { color: 'EF4444', transparency: 70 } })

      if (content.message) {
        sl.addText(content.message, { x: 1.5, y: 2, w: 10, h: 1.2, fontSize: 28, color: 'FFFFFF', align: 'center', bold: true })
      }
      if (content.next_topic) {
        sl.addText(`下节预告：${content.next_topic}`, { x: 2.5, y: 3.5, w: 8, h: 0.6, fontSize: 14, color: 'FEF3C7', align: 'center', fill: { color: 'D97706', transparency: 50 }, rectRadius: 0.15 })
      }
      if (content.review_tip) {
        sl.addText(content.review_tip, { x: 2.5, y: 4.3, w: 8, h: 0.5, fontSize: 12, color: 'FEF3C7', align: 'center', italic: true })
      }
      if (slide.notes) sl.addNotes(slide.notes)
      return
    }

    // --- 其他页面：顶部彩色标题栏 + 底部页码 ---
    const gradientColor = config.color.replace('#', '')
    sl.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 13.33, h: 0.9, fill: { color: gradientColor } })
    sl.addText(slide.title || '', { x: 0.6, y: 0.1, w: 10, h: 0.7, fontSize: 18, color: 'FFFFFF', bold: true })
    sl.addText(config.label, { x: 11, y: 0.15, w: 2, h: 0.6, fontSize: 10, color: 'E0E7FF', align: 'right' })
    // 底部装饰线
    sl.addShape(pptx.ShapeType.rect, { x: 0, y: 7.3, w: 13.33, h: 0.06, fill: { color: gradientColor, transparency: 80 } })
    // 右下角页码
    sl.addText(`${slide.index !== undefined ? slide.index + 1 : ''}`, { x: 12.2, y: 7.0, w: 1, h: 0.3, fontSize: 9, color: '94A3B8', align: 'right' })

    // 添加备注（所有非cover/ending页面）
    if (slide.notes) sl.addNotes(slide.notes)

    // --- intro ---
    if (type === 'intro') {
      if (content.scene) {
        sl.addShape(pptx.ShapeType.roundRect, { x: 1, y: 1.3, w: 11.33, h: 1.2, fill: { color: 'FEF3C7' }, rectRadius: 0.15, line: { color: 'FDE68A', width: 1 } })
        sl.addText('真实场景', { x: 1.3, y: 1.4, w: 2, h: 0.35, fontSize: 10, color: 'B45309', bold: true })
        sl.addText(content.scene, { x: 1.3, y: 1.75, w: 10.5, h: 0.6, fontSize: 16, color: '92400E', bold: true })
      }
      if (content.question) {
        sl.addShape(pptx.ShapeType.roundRect, { x: 1.5, y: 2.8, w: 10.33, h: 1, fill: { color: 'EDE9FE' }, rectRadius: 0.15, line: { color: 'DDD6FE', width: 1 } })
        sl.addText(`💡 ${content.question}`, { x: 1.8, y: 2.95, w: 9.5, h: 0.7, fontSize: 18, color: '4C1D95', bold: true })
      }
      if (content.answer_hint) {
        sl.addText(`💡 ${content.answer_hint}`, { x: 4, y: 4.2, w: 5.33, h: 0.4, fontSize: 12, color: '166534', fill: { color: 'DCFCE7' }, rectRadius: 0.15, align: 'center' })
      }
      return
    }

    // --- concept ---
    if (type === 'concept') {
      // 背景装饰圆
      sl.addShape(pptx.ShapeType.ellipse, { x: 11, y: 0.5, w: 2.5, h: 2.5, fill: { color: 'EEF2FF', transparency: 50 } })
      
      if (content.definition) {
        sl.addShape(pptx.ShapeType.roundRect, { x: 1, y: 1.3, w: 11.33, h: 1.4, fill: { color: 'EEF2FF' }, rectRadius: 0.15 })
        sl.addShape(pptx.ShapeType.rect, { x: 1, y: 1.3, w: 0.08, h: 1.4, fill: { color: '4F46E5' } })
        // 顶部彩色条
        sl.addShape(pptx.ShapeType.rect, { x: 1, y: 1.3, w: 11.33, h: 0.06, fill: { color: '4F46E5' } })
        sl.addText('定义', { x: 1.4, y: 1.4, w: 1.5, h: 0.3, fontSize: 9, color: '4F46E5', bold: true })
        // 去除markdown标记
        const cleanDef = (content.definition || '').replace(/\*\*/g, '')
        sl.addText(cleanDef, { x: 1.4, y: 1.8, w: 10.5, h: 0.7, fontSize: 16, color: '312E81', bold: true })
      }
      if (content.key_attributes?.length) {
        const cols = Math.min(content.key_attributes.length, 3)
        const cardW = (11.33 - (cols - 1) * 0.2) / cols
        content.key_attributes.forEach((attr, idx) => {
          const xOff = 1 + idx * (cardW + 0.2)
          const colors = ['6366F1', '3B82F6', '10B981', 'F59E0B']
          const color = colors[idx % 4]
          sl.addShape(pptx.ShapeType.roundRect, { x: xOff, y: 3.1, w: cardW, h: 1.2, fill: { color: 'FFFFFF' }, rectRadius: 0.12, line: { color: blendColor(color, 0.12), width: 1.5 } })
          // 顶部彩色条
          sl.addShape(pptx.ShapeType.rect, { x: xOff, y: 3.1, w: cardW, h: 0.06, fill: { color } })
          sl.addText(attr.label, { x: xOff + 0.2, y: 3.25, w: cardW - 0.4, h: 0.35, fontSize: 11, color, bold: true, align: 'center' })
          sl.addText(attr.value, { x: xOff + 0.2, y: 3.65, w: cardW - 0.4, h: 0.5, fontSize: 14, color: '334155', align: 'center' })
        })
      }
      if (content.diagram_hint) {
        sl.addShape(pptx.ShapeType.roundRect, { x: 1, y: 4.6, w: 11.33, h: 0.5, fill: { color: 'F5F3FF' }, rectRadius: 0.1, line: { color: 'C4B5FD', width: 0.5, dashType: 'dash' } })
        sl.addText(`📊 ${content.diagram_hint}`, { x: 1.3, y: 4.68, w: 10.5, h: 0.35, fontSize: 10, color: '6D28D9', align: 'center' })
      }
      return
    }

    // --- content ---
    if (type === 'content' && (content.points || content.main_idea)) {
      let yOff = 1.2
      if (content.main_idea) {
        sl.addShape(pptx.ShapeType.roundRect, { x: 1, y: yOff, w: 11.33, h: 0.6, fill: { color: 'DBEAFE' }, rectRadius: 0.12 })
        sl.addShape(pptx.ShapeType.rect, { x: 1, y: yOff, w: 0.06, h: 0.6, fill: { color: '3B82F6' } })
        sl.addText(content.main_idea, { x: 1.4, y: yOff + 0.05, w: 10.5, h: 0.5, fontSize: 15, color: '1E40AF', bold: true })
        yOff += 0.75
      }
      if (content.points) {
        // 限制最多5个要点，超出截断
        const maxPoints = Math.min(content.points.length, 5)
        for (let idx = 0; idx < maxPoints; idx++) {
          const point = content.points[idx]
          const colors = ['6366F1', '3B82F6', '10B981', 'F59E0B', 'EF4444']
          const color = colors[idx % 5]
          sl.addShape(pptx.ShapeType.roundRect, { x: 1, y: yOff, w: 11.33, h: 0.8, fill: { color: 'FFFFFF' }, rectRadius: 0.1, line: { color: blendColor(color, 0.08), width: 1 } })
          sl.addShape(pptx.ShapeType.ellipse, { x: 1.3, y: yOff + 0.15, w: 0.4, h: 0.4, fill: { color: blendColor(color, 0.06) } })
          sl.addText('●', { x: 1.3, y: yOff + 0.15, w: 0.4, h: 0.4, fontSize: 12, color, align: 'center', valign: 'middle' })
          sl.addText(point.title, { x: 2, y: yOff + 0.08, w: 3, h: 0.3, fontSize: 13, color: '1E293B', bold: true })
          const cleanDetail = (point.detail || '').replace(/\*\*/g, '')
          sl.addText(cleanDetail, { x: 2, y: yOff + 0.4, w: 10, h: 0.3, fontSize: 11, color: '64748B' })
          yOff += 0.92
        }
      }
      return
    }

    // --- example ---
    if (type === 'example' && (content.steps || content.case_title)) {
      let yOff = 1.2
      if (content.case_title) {
        sl.addText(`▶  ${content.case_title}`, { x: 1, y: yOff, w: 11, h: 0.4, fontSize: 15, color: '065F46', bold: true })
        yOff += 0.5
      }
      if (content.background) {
        sl.addText(`📋 ${content.background}`, { x: 1, y: yOff, w: 11, h: 0.35, fontSize: 11, color: '166534', fill: { color: 'F0FDF4' }, rectRadius: 0.1 })
        yOff += 0.45
      }
      if (content.steps) {
        const maxSteps = Math.min(content.steps.length, 5)
        for (let idx = 0; idx < maxSteps; idx++) {
          const step = content.steps[idx]
          const colors = ['6366F1', '3B82F6', '10B981', 'F59E0B', 'EF4444']
          const color = colors[idx % 5]
          sl.addShape(pptx.ShapeType.ellipse, { x: 1.2, y: yOff + 0.05, w: 0.35, h: 0.35, fill: { color } })
          sl.addText(`${idx + 1}`, { x: 1.2, y: yOff + 0.05, w: 0.35, h: 0.35, fontSize: 10, color: 'FFFFFF', align: 'center', valign: 'middle', bold: true })
          sl.addText(step.label, { x: 1.8, y: yOff, w: 1.5, h: 0.45, fontSize: 10, color, bold: true })
          sl.addText(step.content, { x: 3.3, y: yOff, w: 9, h: 0.45, fontSize: 12, color: '475569' })
          yOff += 0.58
        }
      }
      if (content.insight) {
        sl.addText(`💡 ${content.insight}`, { x: 1, y: yOff + 0.2, w: 11, h: 0.45, fontSize: 11, color: '92400E', fill: { color: 'FEF3C7' }, rectRadius: 0.1 })
      }
      return
    }

    // --- comparison ---
    if (type === 'comparison' && content.items) {
      const colors = ['6366F1', 'EF4444']
      const itemCount = Math.min(content.items.length, 2)
      content.items.slice(0, itemCount).forEach((item, idx) => {
        const xOff = 1 + idx * 6
        const color = colors[idx % 2]
        sl.addShape(pptx.ShapeType.roundRect, { x: xOff, y: 1.2, w: 5.5, h: 3.8, fill: { color: 'FFFFFF' }, rectRadius: 0.15, line: { color: blendColor(color, 0.15), width: 2 } })
        sl.addShape(pptx.ShapeType.ellipse, { x: xOff + 2.5, y: 1.4, w: 0.12, h: 0.12, fill: { color } })
        sl.addText(item.name, { x: xOff + 0.3, y: 1.6, w: 5, h: 0.5, fontSize: 17, color, bold: true, align: 'center' })
        if (item.features) {
          const maxFeatures = Math.min(item.features.length, 4)
          for (let fi = 0; fi < maxFeatures; fi++) {
            sl.addText(`✓ ${item.features[fi]}`, { x: xOff + 0.5, y: 2.2 + fi * 0.45, w: 4.5, h: 0.35, fontSize: 11, color: '475569' })
          }
        }
      })
      if (content.key_difference) {
        sl.addShape(pptx.ShapeType.roundRect, { x: 2, y: 5.3, w: 9.33, h: 0.6, fill: { color: 'EDE9FE' }, rectRadius: 0.12 })
        sl.addText(`核心区别：${content.key_difference}`, { x: 2.3, y: 5.38, w: 8.5, h: 0.45, fontSize: 13, color: '4C1D95', bold: true, align: 'center' })
      }
      return
    }

    // --- summary ---
    if (type === 'summary' && content.key_takeaways) {
      const maxItems = Math.min(content.key_takeaways.length, 6)
      for (let idx = 0; idx < maxItems; idx++) {
        const item = content.key_takeaways[idx]
        const colors = ['6366F1', '3B82F6', '10B981', 'F59E0B', 'EF4444']
        const color = colors[idx % 5]
        const yOff = 1.2 + idx * 0.78
        // 边界检查
        if (yOff + 0.7 > 7.2) break
        sl.addShape(pptx.ShapeType.roundRect, { x: 1, y: yOff, w: 11.33, h: 0.65, fill: { color: 'FFFFFF' }, rectRadius: 0.1, line: { color: blendColor(color, 0.08), width: 1 } })
        sl.addShape(pptx.ShapeType.roundRect, { x: 1.2, y: yOff + 0.12, w: 0.35, h: 0.35, fill: { color: blendColor(color, 0.06) }, rectRadius: 0.07 })
        sl.addText('✓', { x: 1.2, y: yOff + 0.12, w: 0.35, h: 0.35, fontSize: 12, color, align: 'center', valign: 'middle' })
        sl.addText(item.point, { x: 1.8, y: yOff + 0.08, w: 7, h: 0.45, fontSize: 13, color: '1E293B', bold: true })
        if (item.keyword) {
          sl.addText(item.keyword, { x: 9.5, y: yOff + 0.1, w: 2.5, h: 0.4, fontSize: 10, color, fill: { color: blendColor(color, 0.06) }, rectRadius: 0.07, align: 'center', bold: true })
        }
      }
      if (content.mind_map_hint) {
        const yOff = 1.2 + maxItems * 0.78 + 0.2
        if (yOff < 6.8) {
          sl.addText(`🧠 ${content.mind_map_hint}`, { x: 1, y: yOff, w: 11.33, h: 0.4, fontSize: 10, color: '0369A1', fill: { color: 'E0F2FE' }, rectRadius: 0.08, align: 'center' })
        }
      }
      return
    }

    // --- exercise ---
    if (type === 'exercise' && (content.questions || slide.questions)) {
      const qs = content.questions || slide.questions || []
      const maxQs = Math.min(qs.length, 3)
      const getQText = (q) => q.question_text || q.stem || q.question || q.knowledge_point_name || ''
      const getOptText = (opt) => {
        if (typeof opt === 'string') return opt.replace(/^[A-D]\.\s*/, '')
        if (typeof opt === 'object' && opt !== null) return opt.text || opt.label || String(opt)
        return String(opt)
      }
      for (let idx = 0; idx < maxQs; idx++) {
        const q = qs[idx]
        const yOff = 1.2 + idx * 1.8
        if (yOff + 1.3 > 7.2) break
        sl.addShape(pptx.ShapeType.roundRect, { x: 1, y: yOff, w: 11.33, h: 1.6, fill: { color: 'FFFFFF' }, rectRadius: 0.1, line: { color: 'E2E8F0', width: 1 } })
        sl.addShape(pptx.ShapeType.rect, { x: 1, y: yOff, w: 11.33, h: 0.04, fill: { color: ['EF4444', 'F59E0B', '10B981'][idx % 3] } })
        sl.addShape(pptx.ShapeType.ellipse, { x: 1.3, y: yOff + 0.15, w: 0.3, h: 0.3, fill: { color: 'EF4444' } })
        sl.addText(`${idx + 1}`, { x: 1.3, y: yOff + 0.15, w: 0.3, h: 0.3, fontSize: 10, color: 'FFFFFF', align: 'center', valign: 'middle', bold: true })
        sl.addText(getQText(q), { x: 1.8, y: yOff + 0.1, w: 10, h: 0.35, fontSize: 12, color: '1E293B', bold: true })
        if (q.options) {
          q.options.forEach((opt, oi) => {
            const colIdx = oi % 2
            const rowIdx = Math.floor(oi / 2)
            const optLabel = String.fromCharCode(65 + oi)
            const optText = getOptText(opt)
            sl.addText(`${optLabel}. ${optText}`, { x: 2 + colIdx * 5, y: yOff + 0.55 + rowIdx * 0.4, w: 4.5, h: 0.3, fontSize: 10, color: '475569', fill: { color: 'F8FAFC' }, rectRadius: 0.06 })
          })
        }
      }
      return
    }

    // --- 兜底：通用文本渲染 ---
    const textContent = typeof slide.content === 'string' ? slide.content : JSON.stringify(slide.content, null, 2)
    const cleanText = (textContent || '').replace(/\*\*/g, '')
    sl.addText(cleanText, { x: 1, y: 1.3, w: 11.33, h: 5, fontSize: 14, color: fontColor, valign: 'top' })
  })

  const fileName = `${title || '教学课件'}.pptx`
  await pptx.writeFile({ fileName })
  return fileName
}

// ─────────────────────────────────────────────────────────────────────────────
// 子组件: ChatPPTCard（内联卡片）
// ─────────────────────────────────────────────────────────────────────────────

export function ChatPPTCard({ data, onOpen }) {
  if (!data || !data.success) return null

  const { ppt_type, chapter_title, section_title, slide_count, slides } = data
  const title = ppt_type === 'section' ? section_title : chapter_title
  const slideCount = slide_count || slides?.length || 0
  const Icon = ppt_type === 'section' ? FileTextOutlined : BookOutlined

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.2 }}
      onClick={() => onOpen?.(data)}
      whileHover={{ scale: 1.02, boxShadow: '0 6px 24px rgba(99,102,241,0.4)' }}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 12,
        background: 'linear-gradient(135deg, #1e1b4b 0%, #312e81 100%)',
        borderRadius: 12, padding: '10px 14px', marginTop: 8, cursor: 'pointer',
        boxShadow: '0 4px 16px rgba(99,102,241,0.25)', border: '1px solid rgba(139,92,246,0.3)', maxWidth: 320,
      }}
    >
      <div style={{ width: 36, height: 36, borderRadius: 10, background: 'linear-gradient(135deg, #8b5cf6, #6366f1)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, boxShadow: '0 4px 12px rgba(139,92,246,0.4)' }}>
        <Icon style={{ color: '#fff', fontSize: 16 }} />
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ color: '#fff', fontSize: 13, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {title || '教学幻灯片'}
        </div>
        <Tag style={{ marginTop: 4, background: 'rgba(255,255,255,0.15)', border: 'none', color: 'rgba(255,255,255,0.8)', fontSize: 11, padding: '2px 8px', borderRadius: 6 }}>
          {slideCount} 页
        </Tag>
      </div>
      <div style={{ width: 28, height: 28, borderRadius: 8, background: 'rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
        <RightOutlined style={{ color: 'rgba(255,255,255,0.7)', fontSize: 12 }} />
      </div>
    </motion.div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// 子组件: InlineMiniCard
// ─────────────────────────────────────────────────────────────────────────────

export function InlineMiniCard({ pptData, currentPage, onExpand }) {
  const { slides, ppt_type, chapter_title, section_title } = pptData
  const title = ppt_type === 'section' ? section_title : chapter_title
  const totalSlides = slides?.length || 0
  const progress = totalSlides > 0 ? ((currentPage + 1) / totalSlides) * 100 : 0

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 8 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
      style={{
        marginTop: 12, width: '25%', aspectRatio: '16 / 9', borderRadius: 10,
        background: '#f8fafc', border: '1px solid #e2e8f0', boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
        overflow: 'hidden', cursor: 'pointer', display: 'flex', flexDirection: 'column',
      }}
      onClick={onExpand}
      onMouseEnter={(e) => { e.currentTarget.style.borderColor = '#8b5cf6'; e.currentTarget.style.boxShadow = '0 4px 16px rgba(139,92,246,0.15)'; e.currentTarget.style.transform = 'translateY(-1px)' }}
      onMouseLeave={(e) => { e.currentTarget.style.borderColor = '#e2e8f0'; e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.06)'; e.currentTarget.style.transform = 'translateY(0)' }}
    >
      <div style={{ padding: '8px 12px', borderBottom: '1px solid #f1f5f9', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: '#fff' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ width: 24, height: 24, borderRadius: 6, background: 'linear-gradient(135deg, #8b5cf6, #6366f1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <BookOutlined style={{ color: '#fff', fontSize: 12 }} />
          </div>
          <span style={{ fontSize: 11, fontWeight: 600, color: '#1e293b', maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {title || '教学幻灯片'}
          </span>
        </div>
        <span style={{ fontSize: 10, color: '#94a3b8', fontWeight: 500 }}>{ppt_type === 'section' ? '小节' : '章节'}</span>
      </div>
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '0 12px', gap: 10 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 9, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 2 }}>当前页</div>
          <div style={{ fontSize: 11, color: '#475569', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {slides?.[currentPage]?.title || '幻灯片'}
          </div>
        </div>
        <div style={{ width: 32, height: 32, borderRadius: '50%', background: '#8b5cf6', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 2px 8px rgba(139,92,246,0.3)', flexShrink: 0 }}>
          <PlayCircleOutlined style={{ color: '#fff', fontSize: 16 }} />
        </div>
      </div>
      <div style={{ padding: '6px 12px 8px', display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{ fontSize: 10, color: '#64748b', fontWeight: 600, flexShrink: 0 }}>{currentPage + 1} / {totalSlides}</span>
        <div style={{ flex: 1, height: 2, background: '#e2e8f0', borderRadius: 1, overflow: 'hidden' }}>
          <div style={{ width: `${progress}%`, height: '100%', background: '#8b5cf6', borderRadius: 1, transition: 'width 0.3s ease' }} />
        </div>
      </div>
    </motion.div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// 子组件: FullscreenViewer（全屏查看器）
// ─────────────────────────────────────────────────────────────────────────────

function FullscreenViewer({ pptData, currentPage, onPageChange, onCollapse }) {
  const [direction, setDirection] = useState(0)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [showNotes, setShowNotes] = useState(true)
  const [exporting, setExporting] = useState(false)

  const { slides, ppt_type, chapter_title, section_title } = pptData
  const totalSlides = slides?.length || 0
  const currentSlide = slides?.[currentPage] || {}
  const title = ppt_type === 'section' ? section_title : chapter_title
  const slideConfig = getSlideTypeConfig(currentSlide.type)
  const SlideIcon = slideConfig.icon
  const isFullScreenSlide = ['cover', 'ending'].includes(currentSlide.type)

  const goToNext = useCallback(() => {
    if (currentPage < totalSlides - 1) { setDirection(1); onPageChange?.(currentPage + 1) }
  }, [currentPage, totalSlides, onPageChange])

  const goToPrev = useCallback(() => {
    if (currentPage > 0) { setDirection(-1); onPageChange?.(currentPage - 1) }
  }, [currentPage, onPageChange])

  const goToSlide = useCallback((idx) => {
    if (idx >= 0 && idx < totalSlides && idx !== currentPage) {
      setDirection(idx > currentPage ? 1 : -1); onPageChange?.(idx)
    }
  }, [currentPage, totalSlides, onPageChange])

  const handleExport = useCallback(async () => {
    if (exporting) return
    setExporting(true)
    try {
      const fileName = await exportToPPTX(pptData)
      message.success(`课件已导出：${fileName}`)
    } catch (err) {
      console.error('导出失败:', err)
      message.error('导出失败，请重试')
    } finally {
      setExporting(false)
    }
  }, [pptData, exporting])

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'ArrowLeft') goToPrev()
      else if (e.key === 'ArrowRight' || e.key === ' ') goToNext()
      else if (e.key === 'n') setShowNotes(prev => !prev)
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [goToNext, goToPrev])

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.25 }}
      style={{
        position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, zIndex: 1000,
        background: 'rgba(15,23,42,0.92)', backdropFilter: 'blur(12px)', WebkitBackdropFilter: 'blur(12px)',
        display: 'flex', flexDirection: 'column'
      }}
    >
      {/* 顶部工具栏 */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '10px 20px', background: 'linear-gradient(180deg, rgba(15,23,42,0.98) 0%, rgba(15,23,42,0.8) 100%)',
        position: 'relative', zIndex: 10, borderBottom: '1px solid rgba(139,92,246,0.2)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ width: 34, height: 34, borderRadius: 10, background: 'linear-gradient(135deg, #8b5cf6, #6366f1)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 4px 12px rgba(139,92,246,0.4)' }}>
            <BookOutlined style={{ color: '#fff', fontSize: 15 }} />
          </div>
          <div>
            <div style={{ color: '#fff', fontSize: 13, fontWeight: 600 }}>{ppt_type === 'section' ? '小节' : '章节'}教学课件</div>
            <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: 11 }}>{title}</div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Tag color={slideConfig.color} icon={<SlideIcon />} style={{ fontSize: 11, padding: '3px 10px', borderRadius: 6, margin: 0 }}>
            {slideConfig.label}
          </Tag>
          <span style={{ color: 'rgba(255,255,255,0.7)', fontSize: 13, background: 'rgba(255,255,255,0.08)', padding: '4px 12px', borderRadius: 6 }}>
            {currentPage + 1} / {totalSlides}
          </span>
          
          {/* 导出按钮 */}
          <Tooltip title={exporting ? '导出中...' : '导出PPT'}>
            <button onClick={handleExport} disabled={exporting} style={{
              background: exporting ? 'rgba(99,102,241,0.4)' : 'linear-gradient(135deg, #6366f1, #8b5cf6)',
              border: 'none', borderRadius: 8, padding: '6px 12px', cursor: exporting ? 'wait' : 'pointer',
              display: 'flex', alignItems: 'center', gap: 6,
              color: '#fff', fontSize: 12, fontWeight: 600, transition: 'all 0.2s',
              boxShadow: '0 2px 8px rgba(99,102,241,0.3)'
            }}
              onMouseEnter={(e) => { if (!exporting) e.currentTarget.style.boxShadow = '0 4px 16px rgba(99,102,241,0.5)' }}
              onMouseLeave={(e) => { e.currentTarget.style.boxShadow = '0 2px 8px rgba(99,102,241,0.3)' }}
            >
              <DownloadOutlined style={{ fontSize: 13 }} />
              {exporting ? '导出中...' : '导出'}
            </button>
          </Tooltip>

          <Tooltip title={showNotes ? '隐藏讲稿' : '显示讲稿 (N)'}>
            <button onClick={() => setShowNotes(prev => !prev)} style={{
              background: showNotes ? 'rgba(245,158,11,0.3)' : 'rgba(255,255,255,0.08)',
              border: showNotes ? '1px solid rgba(245,158,11,0.5)' : '1px solid transparent',
              borderRadius: 8, padding: '6px 10px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4,
              color: showNotes ? '#FDE68A' : 'rgba(255,255,255,0.7)', fontSize: 12, transition: 'all 0.2s'
            }}>
              🎤
            </button>
          </Tooltip>
          <Tooltip title="收起">
            <button onClick={onCollapse} style={{
              background: 'rgba(255,255,255,0.08)', border: 'none', borderRadius: 8, padding: '6px 10px',
              cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, color: 'rgba(255,255,255,0.7)', fontSize: 12, transition: 'background 0.2s'
            }}
              onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.15)'}
              onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.08)'}
            >
              <AppstoreOutlined style={{ fontSize: 13 }} /> 收起
            </button>
          </Tooltip>
        </div>
      </div>

      {/* 主内容区 */}
      <div style={{ flex: 1, display: 'flex', position: 'relative', overflow: 'hidden' }}>
        {/* 左侧缩略图导航栏 */}
        <AnimatePresence>
          {!sidebarCollapsed && (
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 200, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.25 }}
              style={{ width: 200, background: 'rgba(30,41,59,0.7)', borderRight: '1px solid rgba(139,92,246,0.15)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}
            >
              <div style={{ padding: '10px 14px', borderBottom: '1px solid rgba(139,92,246,0.15)', color: 'rgba(255,255,255,0.5)', fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 1 }}>
                幻灯片导航
              </div>
              <div style={{ flex: 1, overflowY: 'auto', padding: '6px' }}>
                {slides?.map((slide, idx) => {
                  const isActive = idx === currentPage
                  const config = getSlideTypeConfig(slide.type)
                  const CIcon = config.icon
                  return (
                    <button key={idx} onClick={() => goToSlide(idx)} style={{
                      width: '100%', background: isActive ? 'rgba(139,92,246,0.25)' : 'transparent',
                      border: isActive ? '1px solid rgba(139,92,246,0.4)' : '1px solid transparent',
                      borderRadius: 8, padding: '8px 10px', marginBottom: 4, cursor: 'pointer',
                      display: 'flex', alignItems: 'center', gap: 8, textAlign: 'left', transition: 'all 0.2s'
                    }}
                      onMouseEnter={(e) => { if (!isActive) e.currentTarget.style.background = 'rgba(139,92,246,0.1)' }}
                      onMouseLeave={(e) => { if (!isActive) e.currentTarget.style.background = 'transparent' }}
                    >
                      <div style={{ width: 28, height: 16, borderRadius: 3, background: isActive ? config.gradient : 'rgba(255,255,255,0.1)', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <CIcon style={{ color: isActive ? '#fff' : 'rgba(255,255,255,0.3)', fontSize: 8 }} />
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ color: isActive ? '#fff' : 'rgba(255,255,255,0.75)', fontSize: 11, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {slide.title || '无标题'}
                        </div>
                        <div style={{ color: config.color, fontSize: 9, marginTop: 1 }}>{config.label}</div>
                      </div>
                    </button>
                  )
                })}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* 折叠按钮 */}
        <button onClick={() => setSidebarCollapsed(prev => !prev)} style={{
          position: 'absolute', left: sidebarCollapsed ? 12 : 208, top: '50%', transform: 'translateY(-50%)',
          width: 22, height: 36, background: 'rgba(139,92,246,0.2)', border: 'none', borderRadius: 5,
          cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 5, transition: 'left 0.25s ease'
        }}>
          {sidebarCollapsed ? <MenuUnfoldOutlined style={{ color: 'rgba(255,255,255,0.7)', fontSize: 11 }} /> : <MenuFoldOutlined style={{ color: 'rgba(255,255,255,0.7)', fontSize: 11 }} />}
        </button>

        {/* 幻灯片内容区 */}
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '8px 36px', position: 'relative' }}>
          {/* 左翻页 */}
          <button onClick={goToPrev} disabled={currentPage === 0} style={{
            position: 'absolute', left: 16, top: '50%', transform: 'translateY(-50%)',
            width: 44, height: 44, borderRadius: '50%', border: 'none',
            background: currentPage === 0 ? 'rgba(255,255,255,0.04)' : 'linear-gradient(135deg, #8b5cf6, #6366f1)',
            cursor: currentPage === 0 ? 'not-allowed' : 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: currentPage === 0 ? 'none' : '0 4px 16px rgba(139,92,246,0.4)', transition: 'all 0.2s', opacity: currentPage === 0 ? 0.4 : 1
          }}>
            <LeftOutlined style={{ color: '#fff', fontSize: 16 }} />
          </button>

          {/* 幻灯片卡片 */}
          <AnimatePresence mode="wait" custom={direction}>
            <motion.div
              key={currentPage}
              custom={direction}
              variants={slideVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
              style={{
                width: '100%', maxWidth: 1400, aspectRatio: '16 / 9',
                background: '#fff', borderRadius: 16,
                boxShadow: '0 25px 80px rgba(0,0,0,0.35), 0 0 0 1px rgba(255,255,255,0.05)',
                display: 'flex', flexDirection: 'column', overflow: 'hidden', position: 'relative'
              }}
            >
              {/* 幻灯片标题栏 */}
              {!isFullScreenSlide && (
                <div style={{
                  padding: '12px 28px',
                  background: slideConfig.gradient,
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  flexShrink: 0
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <SlideIcon style={{ color: '#fff', fontSize: 16 }} />
                    <h2 style={{ fontSize: 16, fontWeight: 700, color: '#fff', margin: 0, lineHeight: 1.3 }}>
                      {currentSlide.title || '无标题'}
                    </h2>
                  </div>
                  <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.7)', background: 'rgba(255,255,255,0.15)', padding: '2px 10px', borderRadius: 4 }}>
                    {slideConfig.label}
                  </span>
                </div>
              )}

              {/* 幻灯片内容 */}
              <div style={{ flex: 1, overflow: 'auto', minHeight: 0, padding: 0 }} className="ppt-slide-content">
                <SlideRenderer slide={currentSlide} />
              </div>

              {/* 讲稿区域 - 默认展开 */}
              {showNotes && currentSlide.notes && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  style={{
                    padding: '12px 24px', 
                    background: isFullScreenSlide 
                      ? 'rgba(0,0,0,0.35)' 
                      : 'linear-gradient(135deg, #FFFBEB, #FEF3C7)',
                    borderTop: isFullScreenSlide 
                      ? '1px solid rgba(255,255,255,0.15)' 
                      : '2px solid #F59E0B',
                    flexShrink: 0, maxHeight: 120, overflowY: 'auto'
                  }}
                >
                  <div style={{ 
                    fontSize: 10, fontWeight: 700, 
                    color: isFullScreenSlide ? 'rgba(255,255,255,0.6)' : '#92400E', 
                    marginBottom: 4, display: 'flex', alignItems: 'center', gap: 4 
                  }}>🎤 讲解稿</div>
                  <div style={{ 
                    fontSize: 12, 
                    color: isFullScreenSlide ? 'rgba(255,255,255,0.85)' : '#78350F', 
                    lineHeight: 1.7 
                  }}>{currentSlide.notes}</div>
                </motion.div>
              )}
            </motion.div>
          </AnimatePresence>

          {/* 右翻页 */}
          <button onClick={goToNext} disabled={currentPage === totalSlides - 1} style={{
            position: 'absolute', right: 16, top: '50%', transform: 'translateY(-50%)',
            width: 44, height: 44, borderRadius: '50%', border: 'none',
            background: currentPage === totalSlides - 1 ? 'rgba(255,255,255,0.04)' : 'linear-gradient(135deg, #8b5cf6, #6366f1)',
            cursor: currentPage === totalSlides - 1 ? 'not-allowed' : 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: currentPage === totalSlides - 1 ? 'none' : '0 4px 16px rgba(139,92,246,0.4)', transition: 'all 0.2s', opacity: currentPage === totalSlides - 1 ? 0.4 : 1
          }}>
            <RightOutlined style={{ color: '#fff', fontSize: 16 }} />
          </button>
        </div>
      </div>

      {/* 底部进度条 */}
      <div style={{
        padding: '10px 24px', background: 'linear-gradient(180deg, transparent 0%, rgba(15,23,42,0.9) 100%)',
        display: 'flex', alignItems: 'center', gap: 12
      }}>
        <span style={{ color: 'rgba(255,255,255,0.6)', fontSize: 12, minWidth: 80 }}>
          第 {currentPage + 1} 页 / 共 {totalSlides} 页
        </span>
        <div style={{ flex: 1, height: 4, background: 'rgba(255,255,255,0.1)', borderRadius: 2, overflow: 'hidden' }}>
          <motion.div
            initial={false}
            animate={{ width: `${((currentPage + 1) / totalSlides) * 100}%` }}
            transition={{ duration: 0.3 }}
            style={{ height: '100%', background: slideConfig.gradient, borderRadius: 2 }}
          />
        </div>
        <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.3)' }}>按 N 键切换讲稿</span>
      </div>
    </motion.div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// 主组件: ChatPPTVisualizer
// ─────────────────────────────────────────────────────────────────────────────

export default function ChatPPTVisualizer({ 
  pptData, 
  viewMode = 'fullscreen',
  currentPage = 0,
  onPageChange,
  onCollapse,
  onExpand 
}) {
  if (!pptData?.success || viewMode === 'hidden') return null

  if (viewMode === 'fullscreen') {
    return (
      <AnimatePresence>
        <FullscreenViewer
          pptData={pptData}
          currentPage={currentPage}
          onPageChange={onPageChange}
          onCollapse={onCollapse}
        />
      </AnimatePresence>
    )
  }

  if (viewMode === 'inline') {
    return <InlineMiniCard pptData={pptData} currentPage={currentPage} onExpand={onExpand} />
  }

  return null
}
