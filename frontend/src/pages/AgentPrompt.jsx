import { useState, useEffect } from 'react'
import { Input, Button, message, Card, Modal, Tag, Tooltip } from 'antd'
import {
  SaveOutlined,
  ReloadOutlined,
  ArrowLeftOutlined,
  FileTextOutlined,
  InfoCircleOutlined,
  UndoOutlined,
  ThunderboltOutlined,
  HeartOutlined,
  ReadOutlined,
  UserOutlined,
  PlusOutlined,
  DeleteOutlined,
  StarOutlined,
  RobotOutlined,
} from '@ant-design/icons'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { agentPromptAPI } from '../utils/api'

// 预设提示词模板
const PRESET_TEMPLATES = [
  {
    id: 'strict',
    name: '严格教师型',
    avatar: '小冰',
    icon: 'ThunderboltOutlined',
    color: '#ef4444',
    gradient: 'linear-gradient(135deg, #ef4444, #f97316)',
    description: '严厉、直接、不客气，多批评少表扬',
    prompt: `# AI Tutor - 小冰

**角色**：严格的教师。

## 回复规范
- 一句话回复，简洁直接
- 语气严厉、不客气
- 多批评，少表扬
- 学生不客气则批评回去
- 指出愚蠢问题并批评`,
  },
  {
    id: 'gentle',
    name: '温柔鼓励型',
    avatar: '小智',
    icon: 'HeartOutlined',
    color: '#10b981',
    gradient: 'linear-gradient(135deg, #10b981, #06b6d4)',
    description: '鼓励为主、像朋友聊天、生活化举例',
    prompt: `# AI Tutor - 小智

**角色**：温柔鼓励的学习伙伴。

## 回复规范
- 一句话回复，简洁直接
- 鼓励为主，不批评
- 用生活化例子帮助理解
- 像朋友一样聊天`,
  },
  {
    id: 'academic',
    name: '学术导师型',
    avatar: '小博',
    icon: 'ReadOutlined',
    color: '#6366f1',
    gradient: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
    description: '严谨专业、苏格拉底式提问、深入分析',
    prompt: `# AI Tutor - 小博

**角色**：学术严谨的导师。

## 回复规范
- 一句话回复，简洁直接
- 准确专业，概念给明确定义
- 苏格拉底式提问引导思考
- 温和但坚定地纠正错误
- 适度拓展知识关联`,
  },
]

// 用户自定义模板的存储key
const CUSTOM_TEMPLATES_KEY = 'mindguide_custom_prompt_templates'

// 自定义模板可选的渐变色和头像
const CUSTOM_COLORS = [
  { color: '#0ea5e9', gradient: 'linear-gradient(135deg, #0ea5e9, #06b6d4)' },
  { color: '#8b5cf6', gradient: 'linear-gradient(135deg, #8b5cf6, #a78bfa)' },
  { color: '#f43f5e', gradient: 'linear-gradient(135deg, #f43f5e, #fb7185)' },
  { color: '#f59e0b', gradient: 'linear-gradient(135deg, #f59e0b, #fbbf24)' },
  { color: '#14b8a6', gradient: 'linear-gradient(135deg, #14b8a6, #2dd4bf)' },
  { color: '#ec4899', gradient: 'linear-gradient(135deg, #ec4899, #f472b6)' },
]

// 从localStorage加载用户自定义模板
const loadCustomTemplates = () => {
  try {
    const raw = localStorage.getItem(CUSTOM_TEMPLATES_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

// 保存用户自定义模板到localStorage
const saveCustomTemplates = (templates) => {
  localStorage.setItem(CUSTOM_TEMPLATES_KEY, JSON.stringify(templates))
}

// 生成唯一ID
const genId = () => 'custom_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8)

function AgentPrompt() {
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [customPrompt, setCustomPrompt] = useState('')
  const [defaultPrompt, setDefaultPrompt] = useState('')
  const [hasCustom, setHasCustom] = useState(false)
  const [resetModalVisible, setResetModalVisible] = useState(false)
  const [selectedPreset, setSelectedPreset] = useState(null)
  // 用户自定义模板
  const [userTemplates, setUserTemplates] = useState(loadCustomTemplates)
  // 添加模板弹窗
  const [addModalVisible, setAddModalVisible] = useState(false)
  const [newTemplateName, setNewTemplateName] = useState('')
  const [newTemplateDesc, setNewTemplateDesc] = useState('')
  const [newTemplateAvatar, setNewTemplateAvatar] = useState('')
  // AI生成相关
  const [generating, setGenerating] = useState(false)
  const [generatedPrompt, setGeneratedPrompt] = useState('')

  // 合并内置 + 用户自定义模板
  const allTemplates = [...PRESET_TEMPLATES, ...userTemplates]

  // 根据当前编辑内容判断匹配哪个预设
  const detectPreset = (text) => {
    const trimmed = (text || '').trim()
    for (const t of allTemplates) {
      if (trimmed === t.prompt.trim()) return t.id
    }
    return null
  }

  const navigate = useNavigate()

  useEffect(() => {
    fetchPrompt()
  }, [])

  const fetchPrompt = async () => {
    setLoading(true)
    try {
      const response = await agentPromptAPI.getPrompt()
      const data = response.data.data
      const defaultP = data.default_prompt || ''
      const customP = data.custom_prompt || ''
      setDefaultPrompt(defaultP)
      // 如果用户没有自定义，默认把当前生效的提示词（即默认提示词）填入编辑框，方便直接修改
      const activePrompt = customP || defaultP
      setCustomPrompt(activePrompt)
      setHasCustom(data.has_custom || false)
      setSelectedPreset(detectPreset(activePrompt))
    } catch (error) {
      message.error('获取提示词失败')
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      // 如果保存内容和默认提示词完全一致，视为恢复默认（保存空字符串）
      const promptToSave = customPrompt.trim() === defaultPrompt.trim() ? '' : customPrompt
      const response = await agentPromptAPI.savePrompt(promptToSave)
      if (response.data.success) {
        message.success('提示词已保存')
        setHasCustom(Boolean(promptToSave.trim()))
      } else {
        message.error(response.data.message || '保存失败')
      }
    } catch (error) {
      message.error('保存提示词失败')
    } finally {
      setSaving(false)
    }
  }

  const handleReset = () => {
    setResetModalVisible(true)
  }

  const confirmReset = async () => {
    setCustomPrompt('')
    setSelectedPreset(null)
    setResetModalVisible(false)
    setSaving(true)
    try {
      const response = await agentPromptAPI.savePrompt('')
      if (response.data.success) {
        message.success('已恢复默认提示词')
        setHasCustom(false)
      } else {
        message.error(response.data.message || '恢复失败')
      }
    } catch (error) {
      message.error('恢复默认提示词失败')
    } finally {
      setSaving(false)
    }
  }

  const handleRestoreDefault = () => {
    Modal.confirm({
      title: '恢复默认提示词',
      content: '确定要将当前编辑内容替换为默认提示词吗？此操作会覆盖当前自定义内容。',
      okText: '替换',
      cancelText: '取消',
      onOk: () => {
        setCustomPrompt(defaultPrompt)
        setSelectedPreset(detectPreset(defaultPrompt))
        message.info('已加载默认提示词，请保存后生效')
      },
    })
  }

  // 选择预设模板
  const handleSelectPreset = (template) => {
    setCustomPrompt(template.prompt)
    setSelectedPreset(template.id)
    message.info(`已加载「${template.name} - ${template.avatar}」模板，可继续修改后保存`)
  }

  // 打开添加模板弹窗（不要求编辑区有内容）
  const handleSaveAsTemplate = () => {
    setNewTemplateName('')
    setNewTemplateDesc('')
    setNewTemplateAvatar('')
    setGeneratedPrompt('')
    setAddModalVisible(true)
  }

  // AI生成提示词
  const handleAIGenerate = async () => {
    const name = newTemplateName.trim()
    const desc = newTemplateDesc.trim()
    if (!name) {
      message.warning('请先填写模板名称')
      return
    }
    if (!desc) {
      message.warning('请先填写简短描述')
      return
    }
    setGenerating(true)
    try {
      const response = await agentPromptAPI.generatePrompt(name, desc)
      if (response.data.success) {
        const prompt = response.data.data.prompt || ''
        setGeneratedPrompt(prompt)
        // 同时更新编辑区
        setCustomPrompt(prompt)
        setSelectedPreset(detectPreset(prompt))
        message.success('AI生成提示词成功')
      } else {
        message.error(response.data.message || 'AI生成失败')
      }
    } catch (error) {
      message.error('AI生成提示词失败，请检查模型配置')
    } finally {
      setGenerating(false)
    }
  }

  const confirmAddTemplate = () => {
    const name = newTemplateName.trim()
    if (!name) {
      message.warning('请输入模板名称')
      return
    }
    // 优先使用AI生成的提示词，其次使用编辑区内容
    const promptContent = generatedPrompt.trim() || customPrompt.trim()
    if (!promptContent) {
      message.warning('提示词内容为空，请先编辑或使用AI生成')
      return
    }
    const colorIdx = userTemplates.length % CUSTOM_COLORS.length
    const colorInfo = CUSTOM_COLORS[colorIdx]
    const newTemplate = {
      id: genId(),
      name,
      avatar: newTemplateAvatar.trim() || '自定义',
      color: colorInfo.color,
      gradient: colorInfo.gradient,
      description: newTemplateDesc.trim() || '用户自定义模板',
      prompt: promptContent,
      isCustom: true,
    }
    const updated = [...userTemplates, newTemplate]
    setUserTemplates(updated)
    saveCustomTemplates(updated)
    setAddModalVisible(false)
    setSelectedPreset(newTemplate.id)
    message.success(`模板「${name}」已保存`)
  }

  // 删除用户自定义模板
  const handleDeleteTemplate = (e, templateId) => {
    e.stopPropagation()
    const updated = userTemplates.filter(t => t.id !== templateId)
    setUserTemplates(updated)
    saveCustomTemplates(updated)
    if (selectedPreset === templateId) {
      setSelectedPreset(null)
    }
    message.success('模板已删除')
  }



  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        {/* 返回按钮 */}
        <button
          onClick={() => navigate(-1)}
          style={{
            background: 'none', border: 'none', color: '#64748b', fontSize: 14,
            cursor: 'pointer', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 6,
            padding: 0
          }}
        >
          <ArrowLeftOutlined /> 返回
        </button>

        <div style={{ marginBottom: 24 }}>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: '#1e293b', marginBottom: 8 }}>
            Agent提示词
          </h1>
          <p style={{ color: '#64748b', fontSize: 14 }}>
            自定义 AI Tutor 的角色、使命和回复风格
          </p>
        </div>

        {/* 预设模板选择 */}
        <Card
          style={{ marginBottom: 20, borderRadius: 16 }}
          title={
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{
                width: 36, height: 36, borderRadius: 10,
                background: 'linear-gradient(135deg, #f59e0b, #f97316)',
                display: 'flex', alignItems: 'center', justifyContent: 'center'
              }}>
                <UserOutlined style={{ color: '#fff', fontSize: 18 }} />
              </div>
              <span style={{ fontWeight: 600 }}>预设模板</span>
              <span style={{ fontSize: 12, color: '#94a3b8', fontWeight: 400 }}>点击选择，可在编辑区进一步修改</span>
            </div>
          }
          extra={
            <Button
              size="small"
              type="dashed"
              icon={<PlusOutlined />}
              onClick={handleSaveAsTemplate}
              style={{ borderRadius: 8, fontSize: 12 }}
            >
              存为模板
            </Button>
          }
        >
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 12 }}>
            {allTemplates.map((t) => {
              const isActive = selectedPreset === t.id
              return (
                <div
                  key={t.id}
                  onClick={() => handleSelectPreset(t)}
                  style={{
                    border: `2px solid ${isActive ? t.color : '#e2e8f0'}`,
                    borderRadius: 14,
                    padding: '16px 16px 14px',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    background: isActive ? `${t.color}08` : '#fff',
                    boxShadow: isActive ? `0 2px 8px ${t.color}20` : 'none',
                    position: 'relative',
                  }}
                >
                  {isActive && (
                    <div style={{
                      position: 'absolute', top: 8, right: t.isCustom ? 36 : 8,
                      background: t.color, color: '#fff',
                      borderRadius: 6, fontSize: 10, padding: '1px 6px', fontWeight: 600,
                    }}>当前</div>
                  )}
                  {t.isCustom && (
                    <Tooltip title="删除此模板">
                      <div
                        onClick={(e) => handleDeleteTemplate(e, t.id)}
                        style={{
                          position: 'absolute', top: 8, right: 8,
                          width: 22, height: 22, borderRadius: 6,
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          background: '#fee2e2', color: '#ef4444',
                          cursor: 'pointer', fontSize: 11,
                          transition: 'all 0.15s',
                        }}
                        onMouseEnter={e => { e.currentTarget.style.background = '#fecaca' }}
                        onMouseLeave={e => { e.currentTarget.style.background = '#fee2e2' }}
                      >
                        <DeleteOutlined />
                      </div>
                    </Tooltip>
                  )}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
                    <div style={{
                      width: 40, height: 40, borderRadius: 12,
                      background: t.gradient,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      flexShrink: 0,
                    }}>
                      <span style={{ color: '#fff', fontSize: 16, fontWeight: 700 }}>{t.avatar}</span>
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontWeight: 700, fontSize: 14, color: '#1e293b', display: 'flex', alignItems: 'center', gap: 6 }}>
                        {t.name}
                        {t.isCustom && <Tag color="orange" style={{ fontSize: 10, lineHeight: '16px', padding: '0 4px', margin: 0, borderRadius: 4 }}>自定义</Tag>}
                      </div>
                      <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 1 }}>{t.avatar}</div>
                    </div>
                  </div>
                  <div style={{ fontSize: 12, color: '#64748b', lineHeight: 1.6 }}>
                    {t.description}
                  </div>
                </div>
              )
            })}
          </div>
        </Card>

        {/* 编辑区域 */}
        <Card
          style={{ marginBottom: 20, borderRadius: 16 }}
          title={
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{
                width: 36, height: 36, borderRadius: 10,
                background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                display: 'flex', alignItems: 'center', justifyContent: 'center'
              }}>
                <FileTextOutlined style={{ color: '#fff', fontSize: 18 }} />
              </div>
              <span style={{ fontWeight: 600 }}>自定义提示词</span>
              {hasCustom && (
                <Tag color="purple" style={{ marginLeft: 4 }}>已自定义</Tag>
              )}
            </div>
          }
          extra={
            <div style={{ display: 'flex', gap: 8 }}>
              <Button
                size="small"
                icon={<UndoOutlined />}
                onClick={handleRestoreDefault}
                style={{ borderRadius: 8, fontSize: 12 }}
              >
                填入默认
              </Button>
            </div>
          }
          loading={loading}
        >
          <Input.TextArea
            value={customPrompt}
            onChange={e => {
              setCustomPrompt(e.target.value)
              setSelectedPreset(detectPreset(e.target.value))
            }}
            placeholder="在此输入自定义系统提示词，留空则使用默认提示词..."
            rows={12}
            style={{
              borderRadius: 12,
              fontFamily: '"SF Mono", "Fira Code", monospace',
              fontSize: 13,
              lineHeight: 1.7,
              resize: 'vertical',
            }}
          />
          <div style={{
            marginTop: 12,
            padding: '10px 14px',
            background: 'rgba(99,102,241,0.04)',
            borderRadius: 10,
            fontSize: 12,
            color: '#64748b',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}>
            <InfoCircleOutlined style={{ color: '#6366f1', fontSize: 13 }} />
            <span>当前字数：{customPrompt.length} 字 {customPrompt.length > 8000 && <span style={{ color: '#f43f5e' }}>（提示词较长，可能导致请求失败）</span>}</span>
          </div>
        </Card>

        {/* 操作按钮 */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12 }}>
          {hasCustom && (
            <Button
              onClick={handleReset}
              icon={<ReloadOutlined />}
              style={{ borderRadius: 10 }}
            >
              恢复默认
            </Button>
          )}
          <Button
            onClick={fetchPrompt}
            icon={<ReloadOutlined />}
            style={{ borderRadius: 10 }}
          >
            重置
          </Button>
          <Button
            type="primary"
            onClick={handleSave}
            loading={saving}
            icon={<SaveOutlined />}
            style={{
              borderRadius: 10,
              background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
              border: 'none',
            }}
          >
            保存提示词
          </Button>
        </div>

        {/* 使用说明 */}
        <Card
          style={{ marginBottom: 0, borderRadius: 16 }}
          title={
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{
                width: 36, height: 36, borderRadius: 10,
                background: 'linear-gradient(135deg, #10b981, #06b6d4)',
                display: 'flex', alignItems: 'center', justifyContent: 'center'
              }}>
                <InfoCircleOutlined style={{ color: '#fff', fontSize: 18 }} />
              </div>
              <span style={{ fontWeight: 600 }}>使用说明</span>
            </div>
          }
        >
          <div style={{ fontSize: 13, color: '#475569', lineHeight: 1.7 }}>
            <p style={{ marginBottom: 8 }}>
              编辑<strong>静态提示词</strong>（角色、使命、回复风格）。工具列表、用户信息等动态内容由后端自动拼接。
            </p>
            <p style={{ color: '#94a3b8', marginBottom: 0 }}>
              留空则使用默认提示词。修改后点击保存即时生效。
            </p>
          </div>
        </Card>
      </motion.div>

      {/* 恢复默认确认弹窗 */}
      <Modal
        title="恢复默认提示词"
        open={resetModalVisible}
        onOk={confirmReset}
        onCancel={() => setResetModalVisible(false)}
        okText="恢复"
        cancelText="取消"
        okButtonProps={{ danger: true, style: { borderRadius: 10 } }}
        cancelButtonProps={{ style: { borderRadius: 10 } }}
      >
        <p style={{ color: '#475569' }}>
          确定要清除自定义提示词并恢复为默认内容吗？
        </p>
        <p style={{ color: '#94a3b8', fontSize: 13, marginTop: 8 }}>
          此操作不可撤销，但你可以随时重新自定义。
        </p>
      </Modal>

      {/* 添加自定义模板弹窗 */}
      <Modal
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <StarOutlined style={{ color: '#f59e0b' }} />
            <span>添加模板</span>
          </div>
        }
        open={addModalVisible}
        onOk={confirmAddTemplate}
        onCancel={() => setAddModalVisible(false)}
        okText="保存模板"
        cancelText="取消"
        okButtonProps={{ style: { borderRadius: 10 } }}
        cancelButtonProps={{ style: { borderRadius: 10 } }}
        width={560}
      >
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 13, color: '#64748b', marginBottom: 12 }}>
            填写模板名称和描述，可调用AI自动生成提示词，也可保存当前编辑区内容。
          </div>
          <div style={{ marginBottom: 12 }}>
            <label style={{ display: 'block', fontSize: 13, fontWeight: 600, color: '#1e293b', marginBottom: 4 }}>
              模板名称 <span style={{ color: '#ef4444' }}>*</span>
            </label>
            <Input
              value={newTemplateName}
              onChange={e => setNewTemplateName(e.target.value)}
              placeholder="例如：幽默导师型"
              maxLength={20}
              style={{ borderRadius: 8 }}
            />
          </div>
          <div style={{ marginBottom: 12 }}>
            <label style={{ display: 'block', fontSize: 13, fontWeight: 600, color: '#1e293b', marginBottom: 4 }}>
              AI名称
            </label>
            <Input
              value={newTemplateAvatar}
              onChange={e => setNewTemplateAvatar(e.target.value)}
              placeholder='例如：小乐（留空默认“自定义”）'
              maxLength={4}
              style={{ borderRadius: 8 }}
            />
          </div>
          <div style={{ marginBottom: 12 }}>
            <label style={{ display: 'block', fontSize: 13, fontWeight: 600, color: '#1e293b', marginBottom: 4 }}>
              简短描述 <span style={{ color: '#ef4444' }}>*</span>
              <span style={{ color: '#94a3b8', fontWeight: 400 }}> — AI将根据描述生成提示词</span>
            </label>
            <div style={{ display: 'flex', gap: 8 }}>
              <Input
                value={newTemplateDesc}
                onChange={e => setNewTemplateDesc(e.target.value)}
                placeholder="例如：幽默风趣、喜欢讲段子助学生理解"
                maxLength={40}
                style={{ borderRadius: 8, flex: 1 }}
              />
              <Button
                type="primary"
                icon={<RobotOutlined />}
                loading={generating}
                onClick={handleAIGenerate}
                style={{
                  borderRadius: 8,
                  background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                  border: 'none',
                  whiteSpace: 'nowrap',
                }}
              >
                {generating ? '生成中...' : 'AI生成'}
              </Button>
            </div>
          </div>
      
          {/* AI生成结果预览 */}
          {generatedPrompt && (
            <div style={{ marginBottom: 12 }}>
              <label style={{ display: 'block', fontSize: 13, fontWeight: 600, color: '#1e293b', marginBottom: 4 }}>
                AI生成结果
                <span style={{ color: '#10b981', fontWeight: 400, marginLeft: 6 }}>已生成 {generatedPrompt.length} 字</span>
              </label>
              <div style={{
                background: '#f8fafc',
                border: '1px solid #e2e8f0',
                borderRadius: 8,
                padding: '10px 12px',
                fontSize: 12,
                color: '#475569',
                lineHeight: 1.6,
                maxHeight: 200,
                overflowY: 'auto',
                fontFamily: '"SF Mono", "Fira Code", monospace',
                whiteSpace: 'pre-wrap',
              }}>
                {generatedPrompt}
              </div>
            </div>
          )}
      
          {!generatedPrompt && (
            <div style={{
              padding: '10px 12px',
              background: '#f8fafc', borderRadius: 8,
              fontSize: 12, color: '#94a3b8',
            }}>
              {customPrompt.trim()
                ? <>提示词将保存当前编辑区的文本（{customPrompt.trim().length} 字），也可点击「AI生成」自动生成</>
                : <>请点击「AI生成」自动生成提示词，或在编辑区填写后再保存</>
              }
            </div>
          )}
        </div>
      </Modal>
    </div>
  )
}

export default AgentPrompt
