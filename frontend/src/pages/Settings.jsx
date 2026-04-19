import { useState, useEffect, useCallback } from 'react'
import { Input, Button, Switch, message, Card, Select, Tooltip, Divider, Tag, Modal, Empty, Popconfirm } from 'antd'
import {
  GlobalOutlined,
  ApiOutlined,
  RobotOutlined,
  CloudServerOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SaveOutlined,
  ReloadOutlined,
  InfoCircleOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ArrowLeftOutlined,
  ThunderboltOutlined,
  LinkOutlined,
  SoundOutlined,
  ExperimentOutlined,
  BookOutlined,
  ProjectOutlined,
  MessageOutlined,
} from '@ant-design/icons'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import apiClient from '../utils/api'

const { Option } = Select

// 模块图标映射
const MODULE_ICONS = {
  knowledge_graph: <ProjectOutlined />,
  learning_plan: <BookOutlined />,
  lesson_ppt: <ThunderboltOutlined />,
  exercise: <ExperimentOutlined />,
  agent: <MessageOutlined />,
}

function Settings() {
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [modelApis, setModelApis] = useState([])
  const [moduleModels, setModuleModels] = useState({})
  const [moduleDefinitions, setModuleDefinitions] = useState([])
  const [tavilyApiKey, setTavilyApiKey] = useState('')
  const [tavilyConfigured, setTavilyConfigured] = useState(false)

  // TTS 相关状态
  const [ttsApis, setTtsApis] = useState([])
  const [ttsModel, setTtsModel] = useState('')
  const [ttsProviderDefinitions, setTtsProviderDefinitions] = useState([])
  const [ttsVoices, setTtsVoices] = useState({})

  // 测试状态
  const [testingModelId, setTestingModelId] = useState(null)
  const [modelTestResults, setModelTestResults] = useState({}) // { modelId: true/false }
  const [testingTavily, setTestingTavily] = useState(false)
  const [tavilyStatus, setTavilyStatus] = useState(null)
  const [testingTtsId, setTestingTtsId] = useState(null)
  const [ttsTestResults, setTtsTestResults] = useState({})

  // 编辑模态框
  const [editModalVisible, setEditModalVisible] = useState(false)
  const [editingModel, setEditingModel] = useState(null) // null=新增, object=编辑

  // TTS 编辑模态框
  const [editTtsModalVisible, setEditTtsModalVisible] = useState(false)
  const [editingTts, setEditingTts] = useState(null)

  const navigate = useNavigate()

  useEffect(() => {
    fetchConfig()
  }, [])

  const fetchConfig = async () => {
    setLoading(true)
    try {
      const response = await apiClient.get('/settings/model-config')
      const data = response.data.data
      setModelApis(data.model_apis || [])
      setModuleModels(data.module_models || {})
      setModuleDefinitions(data.module_definitions || [])
      setTavilyApiKey(data.tavily_api_key || '')
      setTavilyConfigured(data.tavily_configured || false)
      setTtsApis(data.tts_apis || [])
      setTtsModel(data.tts_model || '')
      setTtsProviderDefinitions(data.tts_provider_definitions || [])
      setTtsVoices(data.tts_voices || {})
    } catch (error) {
      message.error('获取配置失败')
    } finally {
      setLoading(false)
    }
  }

  // ========== 模型API管理 ==========

  const handleAddModel = () => {
    setEditingModel(null)
    setEditModalVisible(true)
  }

  const handleEditModel = (model) => {
    setEditingModel({ ...model })
    setEditModalVisible(true)
  }

  const handleDeleteModel = (modelId) => {
    const newApis = modelApis.filter(m => m.id !== modelId)
    setModelApis(newApis)
    // 清除该模型被分配的模块
    const newModuleModels = { ...moduleModels }
    for (const key of Object.keys(newModuleModels)) {
      if (newModuleModels[key] === modelId) {
        newModuleModels[key] = ''
      }
    }
    setModuleModels(newModuleModels)
    message.success('已删除模型')
  }

  const handleSaveModel = (modelData) => {
    if (editingModel) {
      // 编辑模式
      setModelApis(prev => prev.map(m => m.id === editingModel.id ? { ...modelData, id: editingModel.id } : m))
      message.success('模型已更新')
    } else {
      // 新增模式 - 生成临时ID（后端会重新生成）
      const tempId = `temp_${Date.now()}`
      setModelApis(prev => [...prev, { ...modelData, id: tempId }])
      message.success('模型已添加')
    }
    setEditModalVisible(false)
  }

  const handleTestModel = async (model) => {
    setTestingModelId(model.id)
    setModelTestResults(prev => ({ ...prev, [model.id]: null }))

    try {
      const response = await apiClient.post('/settings/test-model', null, {
        params: {
          api_key: model.type === 'custom' ? (model.api_key || '') : '',
          base_url: model.base_url,
          model: model.model,
          provider: model.type === 'ollama' ? 'ollama' : 'custom',
        }
      })

      if (response.data.success) {
        setModelTestResults(prev => ({ ...prev, [model.id]: true }))
        message.success('连接成功！')
      } else {
        setModelTestResults(prev => ({ ...prev, [model.id]: false }))
        message.error(response.data.message || '连接失败')
      }
    } catch (error) {
      setModelTestResults(prev => ({ ...prev, [model.id]: false }))
      message.error('连接测试失败')
    } finally {
      setTestingModelId(null)
    }
  }

  // ========== 模块模型分配 ==========

  const handleModuleModelChange = (moduleId, modelId) => {
    setModuleModels(prev => ({ ...prev, [moduleId]: modelId }))
  }

  // ========== TTS 模型管理 ==========

  const handleAddTts = () => {
    setEditingTts(null)
    setEditTtsModalVisible(true)
  }

  const handleEditTts = (tts) => {
    setEditingTts({ ...tts })
    setEditTtsModalVisible(true)
  }

  const handleDeleteTts = (ttsId) => {
    setTtsApis(prev => prev.filter(t => t.id !== ttsId))
    if (ttsModel === ttsId) {
      setTtsModel('')
    }
    message.success('已删除 TTS 模型')
  }

  const handleSaveTts = (ttsData) => {
    if (editingTts) {
      setTtsApis(prev => prev.map(t => t.id === editingTts.id ? { ...ttsData, id: editingTts.id } : t))
      message.success('TTS 模型已更新')
    } else {
      const tempId = `temp_tts_${Date.now()}`
      setTtsApis(prev => [...prev, { ...ttsData, id: tempId }])
      message.success('TTS 模型已添加')
    }
    setEditTtsModalVisible(false)
  }

  const handleTestTts = async (tts) => {
    setTestingTtsId(tts.id)
    setTtsTestResults(prev => ({ ...prev, [tts.id]: null }))

    try {
      const response = await apiClient.post('/settings/test-tts', null, {
        params: {
          provider: tts.provider,
          api_key: tts.api_key || '',
          base_url: tts.base_url || '',
          model: tts.model || '',
          voice: tts.voice || '',
        }
      })

      if (response.data.success) {
        setTtsTestResults(prev => ({ ...prev, [tts.id]: true }))
        message.success('TTS 连接成功！')
      } else {
        setTtsTestResults(prev => ({ ...prev, [tts.id]: false }))
        message.error(response.data.message || '连接失败')
      }
    } catch (error) {
      setTtsTestResults(prev => ({ ...prev, [tts.id]: false }))
      message.error('TTS 连接测试失败')
    } finally {
      setTestingTtsId(null)
    }
  }

  // ========== Tavily 测试 ==========

  const handleTestTavily = async () => {
    if (!tavilyApiKey || tavilyApiKey.includes('****')) {
      message.warning('请输入新的 Tavily API Key')
      return
    }

    setTestingTavily(true)
    setTavilyStatus(null)

    try {
      const response = await apiClient.post('/settings/test-tavily', null, {
        params: { api_key: tavilyApiKey }
      })

      if (response.data.success) {
        setTavilyStatus(true)
        message.success('Tavily API 连接成功！')
      } else {
        setTavilyStatus(false)
        message.error(response.data.message || '连接失败')
      }
    } catch (error) {
      setTavilyStatus(false)
      message.error('连接测试失败')
    } finally {
      setTestingTavily(false)
    }
  }

  // ========== 保存全部 ==========

  const handleSave = async () => {
    // 检查必填
    for (const api of modelApis) {
      if (!api.name || !api.base_url || !api.model) {
        message.warning(`模型「${api.name || '未命名'}」信息不完整，请补充名称、地址和模型名`)
        return
      }
    }

    setSaving(true)
    try {
      const response = await apiClient.post('/settings/model-config', {
        model_apis: modelApis.map(api => ({
          id: api.id,
          name: api.name,
          type: api.type,
          base_url: api.base_url,
          model: api.model,
          api_key: api.api_key || '',
          supports_thinking: api.supports_thinking || false,
          supports_vision: api.supports_vision || false,
          supports_video: api.supports_video || false,
          supports_audio: api.supports_audio || false,
        })),
        module_models: moduleModels,
        tavily_api_key: tavilyApiKey.includes('****') ? undefined : (tavilyApiKey || undefined),
        tts_apis: ttsApis.map(api => ({
          id: api.id,
          name: api.name,
          provider: api.provider,
          base_url: api.base_url || '',
          model: api.model || '',
          api_key: api.api_key || '',
          voice: api.voice || '',
        })),
        tts_model: ttsModel || undefined,
      })

      if (response.data.success) {
        message.success('配置已保存并生效')
        // 重新加载配置（获取后端生成的正式ID）
        fetchConfig()
      } else {
        message.error(response.data.message || '保存失败')
      }
    } catch (error) {
      message.error('保存配置失败')
    } finally {
      setSaving(false)
    }
  }

  // ========== 获取模型名称 ==========

  const getModelName = useCallback((modelId) => {
    const model = modelApis.find(m => m.id === modelId)
    if (!model) return '未配置'
    return `${model.name} (${model.model})`
  }, [modelApis])

  // ========== 渲染 ==========

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
            模型配置
          </h1>
          <p style={{ color: '#64748b', fontSize: 14 }}>
            添加可用的 AI 模型 API，然后为每个功能模块分配模型
          </p>
        </div>

        {/* 第一段：模型 API 管理 */}
        <Card
          style={{ marginBottom: 20, borderRadius: 16 }}
          title={
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{
                width: 36, height: 36, borderRadius: 10,
                background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                display: 'flex', alignItems: 'center', justifyContent: 'center'
              }}>
                <ApiOutlined style={{ color: '#fff', fontSize: 18 }} />
              </div>
              <span style={{ fontWeight: 600 }}>可用模型</span>
              <Tag color="purple" style={{ marginLeft: 4 }}>{modelApis.length} 个</Tag>
            </div>
          }
          extra={
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleAddModel}
              style={{ borderRadius: 10, background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', border: 'none' }}
            >
              添加模型
            </Button>
          }
        >
          {modelApis.length === 0 ? (
            <Empty
              description="尚未添加任何模型，点击「添加模型」开始配置"
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
              {modelApis.map((model) => {
                const testResult = modelTestResults[model.id]
                return (
                  <motion.div
                    key={model.id}
                    whileHover={{ scale: 1.01 }}
                    style={{
                      padding: '16px',
                      borderRadius: 12,
                      background: 'rgba(241,245,249,0.85)',
                      border: '1.5px solid rgba(226,232,240,0.8)',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 8,
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                          {model.type === 'ollama' ? (
                            <Tag color="cyan" style={{ margin: 0 }}>本地</Tag>
                          ) : (
                            <Tag color="purple" style={{ margin: 0 }}>云端</Tag>
                          )}
                          <span style={{ fontSize: 15, fontWeight: 600, color: '#1e293b' }}>
                            {model.name}
                          </span>
                        </div>
                        <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>
                          <div>{model.model}</div>
                          <div style={{ fontSize: 11, color: '#94a3b8', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {model.base_url}
                          </div>
                        </div>
                      </div>
                      <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
                        {testResult === true && <CheckCircleOutlined style={{ color: '#10b981', fontSize: 16 }} />}
                        {testResult === false && <CloseCircleOutlined style={{ color: '#f43f5e', fontSize: 16 }} />}
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
                      <Button
                        size="small"
                        icon={testResult === true ? <CheckCircleOutlined /> : testResult === false ? <CloseCircleOutlined /> : <LinkOutlined />}
                        onClick={() => handleTestModel(model)}
                        loading={testingModelId === model.id}
                        style={{
                          borderRadius: 8, fontSize: 12,
                          background: testResult === true ? 'rgba(16,185,129,0.1)' : testResult === false ? 'rgba(244,63,94,0.1)' : undefined,
                          borderColor: testResult === true ? '#10b981' : testResult === false ? '#f43f5e' : undefined,
                          color: testResult === true ? '#10b981' : testResult === false ? '#f43f5e' : undefined,
                        }}
                      >
                        {testingModelId === model.id ? '测试中...' : testResult === true ? '已连接' : testResult === false ? '失败' : '测试'}
                      </Button>
                      <Button
                        size="small"
                        icon={<EditOutlined />}
                        onClick={() => handleEditModel(model)}
                        style={{ borderRadius: 8, fontSize: 12 }}
                      >
                        编辑
                      </Button>
                      <Popconfirm
                        title="确定删除此模型？"
                        onConfirm={() => handleDeleteModel(model.id)}
                        okText="删除"
                        cancelText="取消"
                        okButtonProps={{ danger: true }}
                      >
                        <Button
                          size="small"
                          danger
                          icon={<DeleteOutlined />}
                          style={{ borderRadius: 8, fontSize: 12 }}
                        />
                      </Popconfirm>
                    </div>
                  </motion.div>
                )
              })}
            </div>
          )}
        </Card>

        {/* 第二段：TTS 模型管理 */}
        <Card
          style={{ marginBottom: 20, borderRadius: 16 }}
          title={
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{
                width: 36, height: 36, borderRadius: 10,
                background: 'linear-gradient(135deg, #f59e0b, #ef4444)',
                display: 'flex', alignItems: 'center', justifyContent: 'center'
              }}>
                <SoundOutlined style={{ color: '#fff', fontSize: 18 }} />
              </div>
              <span style={{ fontWeight: 600 }}>语音合成模型</span>
              <Tag color="orange" style={{ marginLeft: 4 }}>{ttsApis.length} 个</Tag>
            </div>
          }
          extra={
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleAddTts}
              style={{ borderRadius: 10, background: 'linear-gradient(135deg, #f59e0b, #ef4444)', border: 'none' }}
            >
              添加 TTS
            </Button>
          }
        >
          <div style={{ marginBottom: 12, padding: '12px 16px', background: 'rgba(245,158,11,0.05)', borderRadius: 10 }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
              <InfoCircleOutlined style={{ color: '#f59e0b', marginTop: 3 }} />
              <div style={{ fontSize: 13, color: '#475569', lineHeight: 1.6 }}>
                支持多种 TTS 服务：阿里云百炼、OpenAI 兼容（含硅基流动等）、Edge TTS（免费）。
                <br />添加后请在下方「功能模块模型分配」的语音合成下拉框中选择使用哪个模型。
              </div>
            </div>
          </div>

          {ttsApis.length === 0 ? (
            <Empty
              description="尚未添加 TTS 模型，点击「添加 TTS」开始配置"
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
              {ttsApis.map((tts) => {
                const testResult = ttsTestResults[tts.id]
                const isSelected = ttsModel === tts.id
                return (
                  <motion.div
                    key={tts.id}
                    whileHover={{ scale: 1.01 }}
                    style={{
                      padding: '16px',
                      borderRadius: 12,
                      background: isSelected ? 'rgba(245,158,11,0.06)' : 'rgba(241,245,249,0.85)',
                      border: isSelected ? '2px solid #f59e0b' : '1.5px solid rgba(226,232,240,0.8)',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 8,
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                          <Tag color={
                            tts.provider === 'dashscope' ? 'orange' :
                            tts.provider === 'openai' ? 'green' : 'blue'
                          } style={{ margin: 0 }}>
                            {tts.provider === 'dashscope' ? '阿里云' :
                             tts.provider === 'openai' ? 'OpenAI' : 'Edge'}
                          </Tag>
                          {isSelected && <Tag color="gold" style={{ margin: 0 }}>使用中</Tag>}
                          <span style={{ fontSize: 15, fontWeight: 600, color: '#1e293b' }}>
                            {tts.name}
                          </span>
                        </div>
                        <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>
                          <div>{tts.model || '默认模型'}</div>
                          <div style={{ fontSize: 11, color: '#94a3b8' }}>
                            音色: {tts.voice || '默认'}
                          </div>
                        </div>
                      </div>
                      <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
                        {testResult === true && <CheckCircleOutlined style={{ color: '#10b981', fontSize: 16 }} />}
                        {testResult === false && <CloseCircleOutlined style={{ color: '#f43f5e', fontSize: 16 }} />}
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
                      <Button
                        size="small"
                        icon={testResult === true ? <CheckCircleOutlined /> : testResult === false ? <CloseCircleOutlined /> : <LinkOutlined />}
                        onClick={() => handleTestTts(tts)}
                        loading={testingTtsId === tts.id}
                        style={{
                          borderRadius: 8, fontSize: 12,
                          background: testResult === true ? 'rgba(16,185,129,0.1)' : testResult === false ? 'rgba(244,63,94,0.1)' : undefined,
                          borderColor: testResult === true ? '#10b981' : testResult === false ? '#f43f5e' : undefined,
                          color: testResult === true ? '#10b981' : testResult === false ? '#f43f5e' : undefined,
                        }}
                      >
                        {testingTtsId === tts.id ? '测试中...' : testResult === true ? '已连接' : testResult === false ? '失败' : '测试'}
                      </Button>
                      <Button
                        size="small"
                        icon={<EditOutlined />}
                        onClick={() => handleEditTts(tts)}
                        style={{ borderRadius: 8, fontSize: 12 }}
                      >
                        编辑
                      </Button>
                      <Popconfirm
                        title="确定删除此 TTS 模型？"
                        onConfirm={() => handleDeleteTts(tts.id)}
                        okText="删除"
                        cancelText="取消"
                        okButtonProps={{ danger: true }}
                      >
                        <Button
                          size="small"
                          danger
                          icon={<DeleteOutlined />}
                          style={{ borderRadius: 8, fontSize: 12 }}
                        />
                      </Popconfirm>
                    </div>
                  </motion.div>
                )
              })}
            </div>
          )}
        </Card>

        {/* 第三段：功能模块模型分配 */}
        <Card
          style={{ marginBottom: 20, borderRadius: 16 }}
          title={
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{
                width: 36, height: 36, borderRadius: 10,
                background: 'linear-gradient(135deg, #10b981, #06b6d4)',
                display: 'flex', alignItems: 'center', justifyContent: 'center'
              }}>
                <RobotOutlined style={{ color: '#fff', fontSize: 18 }} />
              </div>
              <span style={{ fontWeight: 600 }}>功能模块模型分配</span>
            </div>
          }
        >
          {modelApis.length === 0 ? (
            <div style={{ padding: '20px 0' }}>
              <div style={{
                padding: '12px 16px', background: 'rgba(245,158,11,0.08)', borderRadius: 10,
                display: 'flex', alignItems: 'center', gap: 10,
              }}>
                <InfoCircleOutlined style={{ color: '#f59e0b' }} />
                <span style={{ fontSize: 13, color: '#92400e' }}>请先在上方添加至少一个可用模型</span>
              </div>
            </div>
          ) : (
            <div>
              {moduleDefinitions.map((mod, index) => (
                <div key={mod.id}>
                  <div style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '14px 0',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12, flex: 1 }}>
                      <div style={{
                        width: 40, height: 40, borderRadius: 10,
                        background: moduleModels[mod.id] ? 'rgba(99,102,241,0.1)' : 'rgba(245,158,11,0.1)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontSize: 18,
                        color: moduleModels[mod.id] ? '#6366f1' : '#f59e0b',
                      }}>
                        {MODULE_ICONS[mod.id] || <RobotOutlined />}
                      </div>
                      <div>
                        <div style={{ fontSize: 14, fontWeight: 600, color: '#1e293b' }}>
                          {mod.name}
                        </div>
                        <div style={{ fontSize: 12, color: '#94a3b8' }}>
                          {mod.description}
                        </div>
                      </div>
                    </div>
                    <Select
                      value={moduleModels[mod.id] || undefined}
                      onChange={(value) => handleModuleModelChange(mod.id, value)}
                      placeholder="选择模型"
                      style={{ width: 260, borderRadius: 10 }}
                      allowClear
                    >
                      {modelApis.map(api => (
                        <Option key={api.id} value={api.id}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                            {api.type === 'ollama' ? (
                              <Tag color="cyan" style={{ margin: 0, fontSize: 10 }}>本地</Tag>
                            ) : (
                              <Tag color="purple" style={{ margin: 0, fontSize: 10 }}>云端</Tag>
                            )}
                            <span>{api.name}</span>
                            <span style={{ color: '#94a3b8', fontSize: 12 }}>({api.model})</span>
                          </div>
                        </Option>
                      ))}
                    </Select>
                  </div>
                  {index < moduleDefinitions.length - 1 && <Divider style={{ margin: 0 }} />}
                </div>
              ))}
            </div>
          )}

          {/* 语音合成 TTS 模型选择 */}
          <Divider style={{ margin: '16px 0' }} />
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '14px 0',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, flex: 1 }}>
              <div style={{
                width: 40, height: 40, borderRadius: 10,
                background: ttsModel ? 'rgba(99,102,241,0.1)' : 'rgba(245,158,11,0.1)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 18,
                color: ttsModel ? '#6366f1' : '#f59e0b',
              }}>
                <SoundOutlined />
              </div>
              <div>
                <div style={{ fontSize: 14, fontWeight: 600, color: '#1e293b' }}>
                  语音合成
                </div>
                <div style={{ fontSize: 12, color: '#94a3b8' }}>
                  {ttsModel
                    ? `当前: ${ttsApis.find(t => t.id === ttsModel)?.name || '未选择'}`
                    : '请先在上方添加 TTS 模型并选择'}
                </div>
              </div>
            </div>
            <Select
              value={ttsModel || undefined}
              onChange={setTtsModel}
              placeholder="选择 TTS 模型"
              style={{ width: 260, borderRadius: 10 }}
              allowClear
            >
              {ttsApis.map(api => (
                <Option key={api.id} value={api.id}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Tag color={
                      api.provider === 'dashscope' ? 'orange' :
                      api.provider === 'openai' ? 'green' : 'blue'
                    } style={{ margin: 0, fontSize: 10 }}>
                      {api.provider === 'dashscope' ? '阿里云' :
                       api.provider === 'openai' ? 'OpenAI' : 'Edge'}
                    </Tag>
                    <span>{api.name}</span>
                    <span style={{ color: '#94a3b8', fontSize: 12 }}>({api.voice})</span>
                  </div>
                </Option>
              ))}
            </Select>
          </div>
        </Card>

        {/* 第四段：联网搜索设置 */}
        <Card
          style={{ marginBottom: 20, borderRadius: 16 }}
          title={
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{
                width: 36, height: 36, borderRadius: 10,
                background: 'linear-gradient(135deg, #10b981, #06b6d4)',
                display: 'flex', alignItems: 'center', justifyContent: 'center'
              }}>
                <GlobalOutlined style={{ color: '#fff', fontSize: 18 }} />
              </div>
              <span style={{ fontWeight: 600 }}>联网搜索</span>
            </div>
          }
        >
          <div style={{ marginBottom: 16, padding: '12px 16px', background: 'rgba(99,102,241,0.05)', borderRadius: 10 }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
              <InfoCircleOutlined style={{ color: '#6366f1', marginTop: 3 }} />
              <div style={{ fontSize: 13, color: '#475569', lineHeight: 1.6 }}>
                <strong>Tavily</strong> 是一个联网搜索工具。配置 API Key 后，AI 可以搜索互联网获取最新信息。
                <br />
                访问 <a href="https://app.tavily.com" target="_blank" rel="noopener noreferrer" style={{ color: '#6366f1' }}>app.tavily.com</a> 获取免费 API Key。
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <Input.Password
              value={tavilyApiKey}
              onChange={e => { setTavilyApiKey(e.target.value); setTavilyStatus(null) }}
              placeholder="输入 Tavily API Key"
              style={{ borderRadius: 10, flex: 1 }}
            />
            <Button
              onClick={handleTestTavily}
              loading={testingTavily}
              icon={tavilyStatus === true ? <CheckCircleOutlined /> : tavilyStatus === false ? <CloseCircleOutlined /> : <ReloadOutlined />}
              style={{
                borderRadius: 10,
                background: tavilyStatus === true ? 'rgba(16,185,129,0.1)' : tavilyStatus === false ? 'rgba(244,63,94,0.1)' : undefined,
                borderColor: tavilyStatus === true ? '#10b981' : tavilyStatus === false ? '#f43f5e' : undefined,
                color: tavilyStatus === true ? '#10b981' : tavilyStatus === false ? '#f43f5e' : undefined,
              }}
            >
              {testingTavily ? '测试中...' : tavilyStatus === true ? '已连接' : tavilyStatus === false ? '连接失败' : '测试'}
            </Button>
          </div>
        </Card>



        {/* 保存按钮 */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12 }}>
          <Button
            onClick={fetchConfig}
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
            保存设置
          </Button>
        </div>
      </motion.div>

      {/* 编辑/添加模型弹窗 */}
      <ModelEditModal
        visible={editModalVisible}
        model={editingModel}
        onSave={handleSaveModel}
        onCancel={() => setEditModalVisible(false)}
      />

      {/* 编辑/添加 TTS 弹窗 */}
      <TtsEditModal
        visible={editTtsModalVisible}
        tts={editingTts}
        ttsProviderDefinitions={ttsProviderDefinitions}
        ttsVoices={ttsVoices}
        onSave={handleSaveTts}
        onCancel={() => setEditTtsModalVisible(false)}
      />
    </div>
  )
}


// ========== 模型编辑弹窗组件 ==========

function ModelEditModal({ visible, model, onSave, onCancel }) {
  const [formState, setFormState] = useState({
    name: '',
    type: 'ollama',
    base_url: 'http://localhost:11434',
    model: '',
    api_key: '',
    supports_thinking: false,
    supports_vision: false,
    supports_video: false,
    supports_audio: false,
  })
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState(null)

  useEffect(() => {
    if (visible) {
      if (model) {
        // 编辑模式
        setFormState({
          name: model.name || '',
          type: model.type || 'ollama',
          base_url: model.base_url || '',
          model: model.model || '',
          api_key: '',  // 不回填key，用户需要重新输入或留空
          supports_thinking: model.supports_thinking || false,
          supports_vision: model.supports_vision || false,
          supports_video: model.supports_video || false,
          supports_audio: model.supports_audio || false,
        })
      } else {
        // 新增模式
        setFormState({
          name: '',
          type: 'ollama',
          base_url: 'http://localhost:11434',
          model: '',
          api_key: '',
          supports_thinking: false,
          supports_vision: false,
          supports_video: false,
          supports_audio: false,
        })
      }
      setTestResult(null)
    }
  }, [visible, model])

  const handleTypeChange = (type) => {
    setFormState(prev => ({
      ...prev,
      type,
      base_url: type === 'ollama' ? 'http://localhost:11434' : '',
      api_key: '',
      supports_thinking: false,
      supports_vision: false,
      supports_video: false,
      supports_audio: false,
    }))
    setTestResult(null)
  }

  const handleTest = async () => {
    if (!formState.base_url || !formState.model) {
      message.warning('请填写服务地址和模型名称')
      return
    }

    if (formState.type === 'custom' && !formState.api_key && !model?.api_key_configured) {
      message.warning('请输入 API Key')
      return
    }

    setTesting(true)
    setTestResult(null)

    try {
      const response = await apiClient.post('/settings/test-model', null, {
        params: {
          api_key: formState.type === 'custom' ? formState.api_key : '',
          base_url: formState.base_url,
          model: formState.model,
          provider: formState.type === 'ollama' ? 'ollama' : 'custom',
        }
      })

      if (response.data.success) {
        setTestResult(true)
        message.success('连接成功！')
      } else {
        setTestResult(false)
        message.error(response.data.message || '连接失败')
      }
    } catch (error) {
      setTestResult(false)
      message.error('连接测试失败')
    } finally {
      setTesting(false)
    }
  }

  const handleSave = () => {
    if (!formState.name.trim()) {
      message.warning('请输入模型名称')
      return
    }
    if (!formState.base_url.trim()) {
      message.warning('请输入服务地址')
      return
    }
    if (!formState.model.trim()) {
      message.warning('请输入模型名称')
      return
    }

    // 编辑模式下，如果用户没有输入新的api_key，保留原来的
    const apiKeyToSave = formState.api_key || (model?.api_key_configured ? '****' : '')

    onSave({
      ...formState,
      api_key: apiKeyToSave,
      id: model?.id,
      api_key_configured: model?.api_key_configured,
    })
  }

  return (
    <Modal
      title={model ? '编辑模型' : '添加模型'}
      open={visible}
      onOk={handleSave}
      onCancel={onCancel}
      okText="保存"
      cancelText="取消"
      width={520}
      okButtonProps={{
        style: { borderRadius: 10, background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', border: 'none' }
      }}
      cancelButtonProps={{ style: { borderRadius: 10 } }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16, padding: '8px 0' }}>
        {/* 类型选择 */}
        <div>
          <label style={{ fontSize: 13, fontWeight: 500, color: '#475569', marginBottom: 6, display: 'block' }}>
            类型
          </label>
          <div style={{ display: 'flex', gap: 12 }}>
            <div
              onClick={() => handleTypeChange('ollama')}
              style={{
                flex: 1, padding: '12px 16px', borderRadius: 10, cursor: 'pointer',
                border: `2px solid ${formState.type === 'ollama' ? '#6366f1' : '#e2e8f0'}`,
                background: formState.type === 'ollama' ? 'rgba(99,102,241,0.05)' : '#fff',
                transition: 'all 0.2s',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <RobotOutlined style={{ fontSize: 18, color: formState.type === 'ollama' ? '#6366f1' : '#94a3b8' }} />
                <div>
                  <div style={{ fontWeight: 600, color: formState.type === 'ollama' ? '#6366f1' : '#64748b' }}>
                    Ollama 本地
                  </div>
                  <div style={{ fontSize: 11, color: '#94a3b8' }}>无需 API Key</div>
                </div>
              </div>
            </div>
            <div
              onClick={() => handleTypeChange('custom')}
              style={{
                flex: 1, padding: '12px 16px', borderRadius: 10, cursor: 'pointer',
                border: `2px solid ${formState.type === 'custom' ? '#6366f1' : '#e2e8f0'}`,
                background: formState.type === 'custom' ? 'rgba(99,102,241,0.05)' : '#fff',
                transition: 'all 0.2s',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <CloudServerOutlined style={{ fontSize: 18, color: formState.type === 'custom' ? '#6366f1' : '#94a3b8' }} />
                <div>
                  <div style={{ fontWeight: 600, color: formState.type === 'custom' ? '#6366f1' : '#64748b' }}>
                    云端 API
                  </div>
                  <div style={{ fontSize: 11, color: '#94a3b8' }}>需要 API Key</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 名称 */}
        <div>
          <label style={{ fontSize: 13, fontWeight: 500, color: '#475569', marginBottom: 6, display: 'block' }}>
            名称 <span style={{ color: '#f43f5e' }}>*</span>
          </label>
          <Input
            value={formState.name}
            onChange={e => setFormState(prev => ({ ...prev, name: e.target.value }))}
            placeholder={formState.type === 'ollama' ? '如：本地 Ollama' : '如：DeepSeek 云端'}
            style={{ borderRadius: 10 }}
          />
        </div>

        {/* 服务地址 */}
        <div>
          <label style={{ fontSize: 13, fontWeight: 500, color: '#475569', marginBottom: 6, display: 'block' }}>
            服务地址 <span style={{ color: '#f43f5e' }}>*</span>
          </label>
          <Input
            value={formState.base_url}
            onChange={e => setFormState(prev => ({ ...prev, base_url: e.target.value }))}
            placeholder={formState.type === 'ollama' ? 'http://localhost:11434' : 'https://api.deepseek.com/v1'}
            style={{ borderRadius: 10 }}
          />
        </div>

        {/* 模型名称 */}
        <div>
          <label style={{ fontSize: 13, fontWeight: 500, color: '#475569', marginBottom: 6, display: 'block' }}>
            模型名称 <span style={{ color: '#f43f5e' }}>*</span>
          </label>
          <Input
            value={formState.model}
            onChange={e => setFormState(prev => ({ ...prev, model: e.target.value }))}
            placeholder={formState.type === 'ollama' ? 'qwen3.5:9B' : 'deepseek-chat, qwen-plus 等'}
            style={{ borderRadius: 10 }}
          />
        </div>

        {/* API Key (仅云端) */}
        {formState.type === 'custom' && (
          <div>
            <label style={{ fontSize: 13, fontWeight: 500, color: '#475569', marginBottom: 6, display: 'block' }}>
              API Key {model?.api_key_configured && <span style={{ color: '#10b981', fontWeight: 400 }}>(已配置，留空保持不变)</span>}
            </label>
            <Input.Password
              value={formState.api_key}
              onChange={e => setFormState(prev => ({ ...prev, api_key: e.target.value }))}
              placeholder="输入 API Key"
              style={{ borderRadius: 10 }}
            />
          </div>
        )}

        {/* 思维链开关 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Switch
            checked={formState.supports_thinking}
            onChange={checked => setFormState(prev => ({ ...prev, supports_thinking: checked }))}
            checkedChildren="思维链"
            unCheckedChildren="思维链"
          />
          <span style={{ fontSize: 13, color: '#64748b' }}>
            启用思维链输出（如 DeepSeek R1、Qwen3）
          </span>
        </div>

        {/* 多模态能力开关 */}
        <div style={{ padding: '12px 16px', background: 'rgba(99,102,241,0.04)', borderRadius: 10 }}>
          <div style={{ fontSize: 13, fontWeight: 500, color: '#475569', marginBottom: 10 }}>
            多模态能力
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Switch
                checked={formState.supports_vision}
                onChange={checked => setFormState(prev => ({ ...prev, supports_vision: checked }))}
                checkedChildren="图片"
                unCheckedChildren="图片"
                size="small"
              />
              <span style={{ fontSize: 13, color: '#64748b' }}>支持图片输入（如 Gemma 4、Qwen-VL）</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Switch
                checked={formState.supports_video}
                onChange={checked => setFormState(prev => ({ ...prev, supports_video: checked }))}
                checkedChildren="视频"
                unCheckedChildren="视频"
                size="small"
              />
              <span style={{ fontSize: 13, color: '#64748b' }}>支持视频输入（如 Gemma 4）</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Switch
                checked={formState.supports_audio}
                onChange={checked => setFormState(prev => ({ ...prev, supports_audio: checked }))}
                checkedChildren="音频"
                unCheckedChildren="音频"
                size="small"
              />
              <span style={{ fontSize: 13, color: '#64748b' }}>支持音频输入（如 Gemma 4、Qwen-Omni）</span>
            </div>
          </div>
        </div>

        {/* 测试连接 */}
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <Button
            onClick={handleTest}
            loading={testing}
            icon={testResult === true ? <CheckCircleOutlined /> : testResult === false ? <CloseCircleOutlined /> : <LinkOutlined />}
            style={{
              borderRadius: 10,
              background: testResult === true ? 'rgba(16,185,129,0.1)' : testResult === false ? 'rgba(244,63,94,0.1)' : undefined,
              borderColor: testResult === true ? '#10b981' : testResult === false ? '#f43f5e' : undefined,
              color: testResult === true ? '#10b981' : testResult === false ? '#f43f5e' : undefined,
            }}
          >
            {testing ? '测试中...' : testResult === true ? '已连接' : testResult === false ? '连接失败' : '测试连接'}
          </Button>
          {testResult === true && (
            <span style={{ fontSize: 12, color: '#10b981' }}>模型连接正常</span>
          )}
        </div>
      </div>
    </Modal>
  )
}


export default Settings


// ========== TTS 编辑弹窗组件 ==========

function TtsEditModal({ visible, tts, ttsProviderDefinitions, ttsVoices, onSave, onCancel }) {
  const [formState, setFormState] = useState({
    name: '',
    provider: 'dashscope',
    base_url: '',
    model: '',
    api_key: '',
    voice: '',
  })
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState(null)

  useEffect(() => {
    if (visible) {
      if (tts) {
        setFormState({
          name: tts.name || '',
          provider: tts.provider || 'dashscope',
          base_url: tts.base_url || '',
          model: tts.model || '',
          api_key: '',
          voice: tts.voice || '',
        })
      } else {
        setFormState({
          name: '',
          provider: 'dashscope',
          base_url: 'https://dashscope.aliyuncs.com/api/v1',
          model: 'qwen3-tts-flash',
          api_key: '',
          voice: 'Cherry',
        })
      }
      setTestResult(null)
    }
  }, [visible, tts])

  // 获取当前 provider 的定义
  const currentProviderDef = ttsProviderDefinitions.find(p => p.id === formState.provider) || {}
  const currentVoices = ttsVoices[formState.provider] || []

  const handleProviderChange = (provider) => {
    const def = ttsProviderDefinitions.find(p => p.id === provider)
    setFormState(prev => ({
      ...prev,
      provider,
      base_url: def?.default_base_url || '',
      model: def?.default_model || '',
      voice: def?.default_voice || '',
      api_key: '',
    }))
    setTestResult(null)
  }

  const handleTest = async () => {
    if (formState.provider !== 'edge' && !formState.base_url) {
      message.warning('请填写服务地址')
      return
    }

    if (formState.provider !== 'edge' && !formState.api_key && !tts?.api_key_configured) {
      message.warning('请输入 API Key')
      return
    }

    setTesting(true)
    setTestResult(null)

    try {
      const response = await apiClient.post('/settings/test-tts', null, {
        params: {
          provider: formState.provider,
          api_key: formState.api_key,
          base_url: formState.base_url,
          model: formState.model,
          voice: formState.voice,
        }
      })

      if (response.data.success) {
        setTestResult(true)
        message.success('TTS 连接成功！')
      } else {
        setTestResult(false)
        message.error(response.data.message || '连接失败')
      }
    } catch (error) {
      setTestResult(false)
      message.error('TTS 连接测试失败')
    } finally {
      setTesting(false)
    }
  }

  const handleSave = () => {
    if (!formState.name.trim()) {
      message.warning('请输入名称')
      return
    }

    // 编辑模式下，如果用户没有输入新的api_key，保留原来的
    const apiKeyToSave = formState.api_key || (tts?.api_key_configured ? '****' : '')

    onSave({
      ...formState,
      api_key: apiKeyToSave,
      id: tts?.id,
      api_key_configured: tts?.api_key_configured,
    })
  }

  return (
    <Modal
      title={tts ? '编辑 TTS 模型' : '添加 TTS 模型'}
      open={visible}
      onOk={handleSave}
      onCancel={onCancel}
      okText="保存"
      cancelText="取消"
      width={560}
      okButtonProps={{
        style: { borderRadius: 10, background: 'linear-gradient(135deg, #f59e0b, #ef4444)', border: 'none' }
      }}
      cancelButtonProps={{ style: { borderRadius: 10 } }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16, padding: '8px 0' }}>
        {/* 提供商类型选择 */}
        <div>
          <label style={{ fontSize: 13, fontWeight: 500, color: '#475569', marginBottom: 6, display: 'block' }}>
            提供商
          </label>
          <div style={{ display: 'flex', gap: 8 }}>
            {ttsProviderDefinitions.map(p => (
              <div
                key={p.id}
                onClick={() => handleProviderChange(p.id)}
                style={{
                  flex: 1, padding: '10px 12px', borderRadius: 10, cursor: 'pointer',
                  border: `2px solid ${formState.provider === p.id ? '#f59e0b' : '#e2e8f0'}`,
                  background: formState.provider === p.id ? 'rgba(245,158,11,0.05)' : '#fff',
                  transition: 'all 0.2s',
                }}
              >
                <div style={{ fontWeight: 600, fontSize: 13, color: formState.provider === p.id ? '#f59e0b' : '#64748b' }}>
                  {p.name.split(' ')[0]}
                </div>
                <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 2 }}>
                  {p.requires_api_key ? '需要 Key' : '免费'}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 名称 */}
        <div>
          <label style={{ fontSize: 13, fontWeight: 500, color: '#475569', marginBottom: 6, display: 'block' }}>
            名称 <span style={{ color: '#f43f5e' }}>*</span>
          </label>
          <Input
            value={formState.name}
            onChange={e => setFormState(prev => ({ ...prev, name: e.target.value }))}
            placeholder={`如: ${currentProviderDef.name || '我的 TTS'}`}
            style={{ borderRadius: 10 }}
          />
        </div>

        {/* 服务地址（非 Edge） */}
        {formState.provider !== 'edge' && (
          <div>
            <label style={{ fontSize: 13, fontWeight: 500, color: '#475569', marginBottom: 6, display: 'block' }}>
              服务地址 <span style={{ color: '#f43f5e' }}>*</span>
            </label>
            <Input
              value={formState.base_url}
              onChange={e => setFormState(prev => ({ ...prev, base_url: e.target.value }))}
              placeholder={currentProviderDef.default_base_url || 'https://...'}
              style={{ borderRadius: 10 }}
            />
          </div>
        )}

        {/* 模型名称（非 Edge） */}
        {formState.provider !== 'edge' && (
          <div>
            <label style={{ fontSize: 13, fontWeight: 500, color: '#475569', marginBottom: 6, display: 'block' }}>
              模型名称
            </label>
            <Input
              value={formState.model}
              onChange={e => setFormState(prev => ({ ...prev, model: e.target.value }))}
              placeholder={currentProviderDef.default_model || '模型名称'}
              style={{ borderRadius: 10 }}
            />
          </div>
        )}

        {/* API Key（需要 Key 的提供商） */}
        {currentProviderDef.requires_api_key && (
          <div>
            <label style={{ fontSize: 13, fontWeight: 500, color: '#475569', marginBottom: 6, display: 'block' }}>
              API Key {tts?.api_key_configured && <span style={{ color: '#10b981', fontWeight: 400 }}>(已配置，留空保持不变)</span>}
            </label>
            <Input.Password
              value={formState.api_key}
              onChange={e => setFormState(prev => ({ ...prev, api_key: e.target.value }))}
              placeholder="输入 API Key"
              style={{ borderRadius: 10 }}
            />
          </div>
        )}

        {/* 音色选择 */}
        <div>
          <label style={{ fontSize: 13, fontWeight: 500, color: '#475569', marginBottom: 6, display: 'block' }}>
            音色
          </label>
          {currentVoices.length > 0 ? (
            <Select
              value={formState.voice || undefined}
              onChange={value => setFormState(prev => ({ ...prev, voice: value }))}
              placeholder="选择音色"
              style={{ width: '100%', borderRadius: 10 }}
              showSearch
              optionFilterProp="children"
            >
              {currentVoices.map(v => (
                <Option key={v.id} value={v.id}>
                  <span>{v.name}</span>
                  <span style={{ color: '#94a3b8', fontSize: 11, marginLeft: 8 }}>({v.id})</span>
                </Option>
              ))}
            </Select>
          ) : (
            <Input
              value={formState.voice}
              onChange={e => setFormState(prev => ({ ...prev, voice: e.target.value }))}
              placeholder={currentProviderDef.default_voice || '默认音色'}
              style={{ borderRadius: 10 }}
            />
          )}
        </div>

        {/* 测试连接 */}
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <Button
            onClick={handleTest}
            loading={testing}
            icon={testResult === true ? <CheckCircleOutlined /> : testResult === false ? <CloseCircleOutlined /> : <LinkOutlined />}
            style={{
              borderRadius: 10,
              background: testResult === true ? 'rgba(16,185,129,0.1)' : testResult === false ? 'rgba(244,63,94,0.1)' : undefined,
              borderColor: testResult === true ? '#10b981' : testResult === false ? '#f43f5e' : undefined,
              color: testResult === true ? '#10b981' : testResult === false ? '#f43f5e' : undefined,
            }}
          >
            {testing ? '测试中...' : testResult === true ? '已连接' : testResult === false ? '连接失败' : '测试连接'}
          </Button>
          {testResult === true && (
            <span style={{ fontSize: 12, color: '#10b981' }}>TTS 连接正常</span>
          )}
        </div>
      </div>
    </Modal>
  )
}
