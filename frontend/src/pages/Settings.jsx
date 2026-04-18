import { useState, useEffect, useMemo } from 'react'
import { Input, Button, Switch, message, Card, Form, Select, Tooltip, Divider, Radio, Collapse, Tag, Badge } from 'antd'
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
  ThunderboltOutlined,
  ArrowLeftOutlined,
  CheckOutlined,
} from '@ant-design/icons'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import apiClient from '../utils/api'

const { Option } = Select
const { Panel } = Collapse

function Settings() {
  const [loading, setLoading] = useState(false)
  const [testingTavily, setTestingTavily] = useState(false)
  const [testingModel, setTestingModel] = useState(false)
  const [tavilyStatus, setTavilyStatus] = useState(null)
  const [modelStatus, setModelStatus] = useState(null)
  const [presets, setPresets] = useState([])
  const [selectedPresetId, setSelectedPresetId] = useState(null)
  const [currentSettings, setCurrentSettings] = useState(null)  // 保存当前配置用于模型选择
  const [verifiedModels, setVerifiedModels] = useState({})  // 已验证可用的模型 { ollama: true, custom: true }
  const [form] = Form.useForm()
  const navigate = useNavigate()

  // 计算可用的模型列表（用于选择）- 只显示已验证的模型
  const availableModels = useMemo(() => {
    if (!currentSettings) return []
    
    const models = []
    
    // 添加 Ollama 模型（如果配置了且已验证）
    if (currentSettings.ollama_model && verifiedModels.ollama) {
      models.push({
        key: 'ollama',
        name: currentSettings.ollama_model,
        provider: 'Ollama 本地',
        type: 'local',
        config: {
          ollama_base_url: currentSettings.ollama_base_url,
          ollama_model: currentSettings.ollama_model,
        }
      })
    }
    
    // 添加 Custom 模型（如果配置了且已验证）
    if (currentSettings.custom_api_base_url && currentSettings.custom_model && 
        (currentSettings.custom_api_key || currentSettings.custom_api_key === '') &&
        verifiedModels.custom) {
      // 从预设中找到匹配的模型名称
      const matchedPreset = presets.find(p => 
        p.base_url === currentSettings.custom_api_base_url && 
        p.model === currentSettings.custom_model
      )
      
      models.push({
        key: 'custom',
        name: currentSettings.custom_model,
        provider: matchedPreset?.name || '自定义 API',
        type: 'cloud',
        config: {
          custom_api_base_url: currentSettings.custom_api_base_url,
          custom_model: currentSettings.custom_model,
          custom_api_key: currentSettings.custom_api_key,
          custom_supports_thinking: currentSettings.custom_supports_thinking,
        }
      })
    }
    
    return models
  }, [currentSettings, presets])

  useEffect(() => {
    fetchSettings()
  }, [])

  const fetchSettings = async () => {
    setLoading(true)
    try {
      const response = await apiClient.get('/settings/current')
      const data = response.data.data
      
      // 保存当前配置用于模型选择
      setCurrentSettings({
        current_provider: data.current_provider || 'ollama',
        ollama_base_url: data.ollama_base_url || 'http://localhost:11434',
        ollama_model: data.ollama_model || 'qwen3.5:9B',
        custom_api_base_url: data.custom_api_base_url || '',
        custom_model: data.custom_model || '',
        custom_api_key: data.custom_api_key || '',
        custom_supports_thinking: data.custom_supports_thinking || false,
      })
      
      // 检查 custom_api_key 是否为掩码值（包含****），如果是则不填充
      const isMaskedKey = data.custom_api_key && data.custom_api_key.includes('****')
      // 判断 Custom 模型是否已配置（返回空字符串表示已配置，None表示未配置）
      const customConfigured = data.custom_api_key !== null && data.custom_api_key !== undefined
      
      form.setFieldsValue({
        current_provider: data.current_provider || 'ollama',
        tavily_api_key: data.tavily_api_key || '',  // 显示掩码值
        ollama_base_url: data.ollama_base_url || 'http://localhost:11434',
        ollama_model: data.ollama_model || 'qwen3.5:9B',
        // 如果是掩码值，不填充 custom_api_key（保留原值）；否则填充
        custom_api_key: isMaskedKey ? undefined : (data.custom_api_key || ''),
        custom_api_base_url: data.custom_api_base_url || 'https://api.openai.com/v1',
        custom_model: data.custom_model || 'gpt-4o-mini',
        custom_supports_thinking: data.custom_supports_thinking || false,
      })
      
      // 如果已经配置了 custom API Key（非掩码），显示配置状态
      if (data.custom_api_base_url && data.custom_model && !isMaskedKey) {
        // 有配置但没有保存过Key
      }
      if (isMaskedKey) {
        console.log('API Key已配置（已掩码），修改时请填写完整Key')
      }
      
      // 如果有预设数据
      if (data.presets) {
        setPresets(data.presets)
        
        // 根据当前配置匹配预设
        const provider = data.current_provider || 'ollama'
        let matchedPreset = null
        
        if (provider === 'ollama') {
          matchedPreset = data.presets.find(p => 
            p.id === 'ollama-local' && 
            p.base_url === data.ollama_base_url && 
            p.model === data.ollama_model
          )
        } else if (provider === 'custom') {
          matchedPreset = data.presets.find(p => 
            p.base_url === data.custom_api_base_url && 
            p.model === data.custom_model &&
            p.id !== 'custom'  // 排除自定义配置预设
          )
          // 如果没有匹配到预设，使用自定义配置
          if (!matchedPreset) {
            matchedPreset = data.presets.find(p => p.id === 'custom')
          }
        }
        
        if (matchedPreset) {
          setSelectedPresetId(matchedPreset.id)
        }
      }
      
      // 如果已经配置，显示状态
      if (data.tavily_configured) {
        setTavilyStatus(true)
      }
    } catch (error) {
      message.error('获取设置失败')
    } finally {
      setLoading(false)
    }
  }
  
  const handleTestTavily = async () => {
    const apiKey = form.getFieldValue('tavily_api_key')
    if (!apiKey) {
      message.warning('请输入 Tavily API Key')
      return
    }
    
    setTestingTavily(true)
    setTavilyStatus(null)
    
    try {
      const response = await apiClient.post('/settings/test-tavily', null, {
        params: { api_key: apiKey }
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
  
  const handleTestModel = async () => {
    const values = form.getFieldsValue()
    const provider = values.current_provider
    
    if (provider === 'custom' && !values.custom_api_key) {
      message.warning('请输入 API Key')
      return
    }
    
    setTestingModel(true)
    setModelStatus(null)
    
    try {
      const response = await apiClient.post('/settings/test-model', null, {
        params: {
          api_key: values.custom_api_key || '',
          base_url: provider === 'ollama' ? values.ollama_base_url : values.custom_api_base_url,
          model: provider === 'ollama' ? values.ollama_model : values.custom_model,
          provider: provider
        }
      })
      
      if (response.data.success) {
        setModelStatus(true)
        // 标记该模型为已验证可用
        setVerifiedModels(prev => ({ ...prev, [provider]: true }))
        message.success(response.data.message || '模型连接成功！')
      } else {
        setModelStatus(false)
        // 测试失败，移除验证状态
        setVerifiedModels(prev => ({ ...prev, [provider]: false }))
        message.error(response.data.message || '连接失败')
      }
    } catch (error) {
      setModelStatus(false)
      // 测试失败，移除验证状态
      setVerifiedModels(prev => ({ ...prev, [provider]: false }))
      message.error('连接测试失败')
    } finally {
      setTestingModel(false)
    }
  }
  
  const handleApplyPreset = (preset) => {
    setSelectedPresetId(preset.id)  // 更新选中的预设ID
    
    if (preset.id === 'custom') {
      // 自定义配置：清空 API 相关字段，切换到 custom 模式
      form.setFieldsValue({
        current_provider: 'custom',
        custom_api_base_url: '',
        custom_model: '',
        custom_supports_thinking: false,
      })
      message.info('请手动填写 API 配置')
      return
    }
    
    form.setFieldsValue({
      current_provider: preset.api_key_required ? 'custom' : 'ollama',
      custom_api_base_url: preset.base_url,
      custom_model: preset.model,
      custom_supports_thinking: preset.supports_thinking,
    })
    message.success(`已应用预设: ${preset.name}`)
  }
  
  // 处理模型选择
  const handleModelSelect = (modelKey) => {
    const model = availableModels.find(m => m.key === modelKey)
    if (!model) return
    
    setSelectedPresetId(modelKey)
    form.setFieldsValue({
      current_provider: model.key,
      ...model.config,
    })
    message.success(`已选择使用: ${model.name}`)
  }
  
  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      
      // 构建更新数据，API Key 只在有新值时才更新
      const updateData = {
        current_provider: values.current_provider,
        ollama_base_url: values.ollama_base_url,
        ollama_model: values.ollama_model,
        custom_api_base_url: values.custom_api_base_url,
        custom_model: values.custom_model,
        custom_supports_thinking: values.custom_supports_thinking,
      }
      
      // 只有当用户填写了新 API Key 时才更新
      if (values.custom_api_key) {
        updateData.custom_api_key = values.custom_api_key
      }
      
      // Tavily API Key 同理
      if (values.tavily_api_key) {
        updateData.tavily_api_key = values.tavily_api_key
      }
      
      const response = await apiClient.post('/settings/update', updateData)
      
      if (response.data.success) {
        message.success(response.data.message)
        if (values.tavily_api_key) {
          setTavilyStatus(true)
        }
        
        // 保存成功后，自动测试模型并标记为已验证
        const testProvider = values.current_provider
        try {
          const testResponse = await apiClient.post('/settings/test-model', null, {
            params: {
              api_key: values.custom_api_key || '',
              base_url: testProvider === 'ollama' ? values.ollama_base_url : values.custom_api_base_url,
              model: testProvider === 'ollama' ? values.ollama_model : values.custom_model,
              provider: testProvider
            }
          })
          
          if (testResponse.data.success) {
            setModelStatus(true)
            // 标记当前选择的模型为已验证
            setVerifiedModels(prev => ({ ...prev, [testProvider]: true }))
          } else {
            setModelStatus(false)
            setVerifiedModels(prev => ({ ...prev, [testProvider]: false }))
            message.warning('设置已保存，但模型连接测试失败，请检查配置')
          }
        } catch (e) {
          setModelStatus(false)
          setVerifiedModels(prev => ({ ...prev, [testProvider]: false }))
        }
        
        // 刷新设置
        fetchSettings()
      } else {
        message.error(response.data.message)
      }
    } catch (error) {
      message.error('保存设置失败')
    }
  }
  
  const currentProvider = Form.useWatch('current_provider', form)
  
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
            设置
          </h1>
          <p style={{ color: '#64748b', fontSize: 14 }}>
            配置 AI 模型和联网搜索功能
          </p>
        </div>
        
        {/* 当前使用的模型选择 */}
        {availableModels.length > 0 && (
          <Card 
            style={{ marginBottom: 20, borderRadius: 16, background: 'linear-gradient(135deg, rgba(99,102,241,0.05), rgba(139,92,246,0.05))' }}
            title={
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{
                  width: 36, height: 36, borderRadius: 10,
                  background: 'linear-gradient(135deg, #10b981, #06b6d4)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center'
                }}>
                  <CheckOutlined style={{ color: '#fff', fontSize: 18 }} />
                </div>
                <span style={{ fontWeight: 600 }}>当前使用的模型</span>
              </div>
            }
          >
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
              {availableModels.map((model) => {
                const isActive = currentSettings?.current_provider === model.key
                return (
                  <motion.div
                    key={model.key}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => handleModelSelect(model.key)}
                    style={{
                      padding: '16px 20px',
                      borderRadius: 12,
                      background: isActive
                        ? 'rgba(16,185,129,0.15)' 
                        : 'rgba(255,255,255,0.8)',
                      border: `2px solid ${
                        isActive ? '#10b981' : 'rgba(226,232,240,0.8)'
                      }`,
                      cursor: 'pointer',
                      transition: 'all 0.2s',
                      minWidth: 200,
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 4,
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      {isActive && <CheckCircleOutlined style={{ color: '#10b981', fontSize: 16 }} />}
                      <span style={{ 
                        fontSize: 15, 
                        fontWeight: 600, 
                        color: isActive ? '#10b981' : '#1e293b' 
                      }}>
                        {model.name}
                      </span>
                    </div>
                    <div style={{ fontSize: 12, color: '#64748b' }}>
                      {model.type === 'local' ? (
                        <Tag color="cyan" style={{ marginRight: 4 }}>本地</Tag>
                      ) : (
                        <Tag color="purple" style={{ marginRight: 4 }}>云端</Tag>
                      )}
                      {model.provider}
                    </div>
                  </motion.div>
                )
              })}
            </div>
            <div style={{ marginTop: 12, padding: '10px 14px', background: 'rgba(99,102,241,0.05)', borderRadius: 8 }}>
              <InfoCircleOutlined style={{ color: '#6366f1', marginRight: 6 }} />
              <span style={{ fontSize: 12, color: '#64748b' }}>
                选择模型后点击「保存设置」使其生效，所有 AI 功能将使用该模型
              </span>
            </div>
          </Card>
        )}
        
        {/* 模型预设 */}
        <Card 
          style={{ marginBottom: 20, borderRadius: 16 }}
          title={
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{
                width: 36, height: 36, borderRadius: 10,
                background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                display: 'flex', alignItems: 'center', justifyContent: 'center'
              }}>
                <ThunderboltOutlined style={{ color: '#fff', fontSize: 18 }} />
              </div>
              <span style={{ fontWeight: 600 }}>快速选择</span>
            </div>
          }
        >
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
            {presets.map((preset) => (
              <motion.div
                key={preset.id}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => handleApplyPreset(preset)}
                style={{
                  padding: '14px 16px',
                  borderRadius: 12,
                  background: preset.id === selectedPresetId
                    ? 'rgba(99,102,241,0.15)' 
                    : 'rgba(241,245,249,0.85)',
                  border: `1.5px solid ${
                    preset.id === selectedPresetId
                      ? '#6366f1' 
                      : 'rgba(226,232,240,0.8)'
                  }`,
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                }}
              >
                <div style={{ fontSize: 13, fontWeight: 600, color: '#1e293b', marginBottom: 4 }}>
                  {preset.name}
                </div>
                <div style={{ fontSize: 11, color: '#64748b', lineHeight: 1.4 }}>
                  {preset.description}
                </div>
                <div style={{ fontSize: 10, color: '#94a3b8', marginTop: 6 }}>
                  {preset.model}
                </div>
              </motion.div>
            ))}
          </div>
        </Card>
        
        {/* 模型设置 */}
        <Card 
          style={{ marginBottom: 20, borderRadius: 16 }}
          title={
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{
                width: 36, height: 36, borderRadius: 10,
                background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                display: 'flex', alignItems: 'center', justifyContent: 'center'
              }}>
                <RobotOutlined style={{ color: '#fff', fontSize: 18 }} />
              </div>
              <span style={{ fontWeight: 600 }}>模型配置</span>
            </div>
          }
        >
          <Form form={form} layout="vertical">
            <Form.Item
              name="current_provider"
              label="选择提供商"
            >
              <Radio.Group buttonStyle="solid">
                <Radio.Button value="ollama">
                  <RobotOutlined style={{ marginRight: 6 }} /> Ollama 本地
                </Radio.Button>
                <Radio.Button value="custom">
                  <CloudServerOutlined style={{ marginRight: 6 }} /> API 云端
                </Radio.Button>
              </Radio.Group>
            </Form.Item>
            
            {currentProvider === 'ollama' ? (
              <>
                <Form.Item
                  name="ollama_base_url"
                  label="Ollama 服务地址"
                  tooltip="本地 Ollama 服务的 API 地址"
                >
                  <Input 
                    placeholder="http://localhost:11434"
                    style={{ borderRadius: 10 }}
                  />
                </Form.Item>
                
                <Form.Item
                  name="ollama_model"
                  label="本地模型"
                  tooltip="Ollama 中已下载的模型名称"
                >
                  <Select style={{ borderRadius: 10 }}>
                    <Option value="qwen3.5:9B">Qwen3.5 9B</Option>
                    <Option value="qwen3.5:4B">Qwen3.5 4B</Option>
                    <Option value="qwen3.5:2B">Qwen3.5 2B</Option>
                    <Option value="qwen3.5:0.8B">Qwen3.5 0.8B</Option>
                  </Select>
                </Form.Item>
              </>
            ) : (
              <>
                <Form.Item
                  name="custom_api_base_url"
                  label="API 端点地址"
                  tooltip="OpenAI 兼容格式的 API 端点"
                >
                  <Input 
                    placeholder="https://api.openai.com/v1"
                    style={{ borderRadius: 10 }}
                  />
                </Form.Item>
                
                <Form.Item
                  name="custom_model"
                  label="模型名称"
                  tooltip="API 提供商支持的模型"
                >
                  <Input 
                    placeholder="gpt-4o-mini, qwen-plus, deepseek-chat 等"
                    style={{ borderRadius: 10 }}
                  />
                </Form.Item>
                
                <Form.Item
                  name="custom_api_key"
                  label="API Key"
                  tooltip="API 提供商的密钥"
                >
                  <Input.Password 
                    placeholder="输入 API Key"
                    style={{ borderRadius: 10 }}
                  />
                </Form.Item>
                
                <Form.Item
                  name="custom_supports_thinking"
                  valuePropName="checked"
                  tooltip="如果模型支持思维链输出（如 DeepSeek R1、Qwen3）可开启"
                >
                  <Switch checkedChildren="思维链" unCheckedChildren="思维链" />
                  <span style={{ marginLeft: 8, fontSize: 13, color: '#64748b' }}>
                    启用思维链输出
                  </span>
                </Form.Item>
              </>
            )}
            
            <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
              <Button
                onClick={handleTestModel}
                loading={testingModel}
                icon={modelStatus === true ? <CheckCircleOutlined /> : modelStatus === false ? <CloseCircleOutlined /> : <ReloadOutlined />}
                style={{ 
                  borderRadius: 10,
                  background: modelStatus === true ? 'rgba(16,185,129,0.1)' : modelStatus === false ? 'rgba(244,63,94,0.1)' : undefined,
                  borderColor: modelStatus === true ? '#10b981' : modelStatus === false ? '#f43f5e' : undefined,
                  color: modelStatus === true ? '#10b981' : modelStatus === false ? '#f43f5e' : undefined,
                }}
              >
                {testingModel ? '测试中...' : modelStatus === true ? '已连接' : modelStatus === false ? '连接失败' : '测试连接'}
              </Button>
              
              {modelStatus === true && (
                <span style={{ fontSize: 12, color: '#10b981' }}>
                  ✓ 模型配置正确
                </span>
              )}
            </div>
          </Form>
        </Card>
        
        {/* 联网搜索设置 */}
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
              <span style={{ fontWeight: 600 }}>联网搜索设置</span>
            </div>
          }
        >
          <div style={{ marginBottom: 16, padding: '12px 16px', background: 'rgba(99,102,241,0.05)', borderRadius: 10 }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
              <InfoCircleOutlined style={{ color: '#6366f1', marginTop: 3 }} />
              <div style={{ fontSize: 13, color: '#475569', lineHeight: 1.6 }}>
                <strong>Tavily</strong> 是一个强大的联网搜索工具。配置 API Key 后，AI 可以搜索互联网获取最新信息来回答你的问题。
                <br />
                访问 <a href="https://app.tavily.com" target="_blank" rel="noopener noreferrer" style={{ color: '#6366f1' }}>app.tavily.com</a> 获取免费 API Key。
              </div>
            </div>
          </div>
          
          <Form form={form} layout="vertical">
            <Form.Item
              name="tavily_api_key"
              label="Tavily API Key"
              tooltip="用于联网搜索的 API Key"
            >
              <Input.Password 
                placeholder="输入你的 Tavily API Key"
                style={{ borderRadius: 10 }}
              />
            </Form.Item>
            
            <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
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
                {testingTavily ? '测试中...' : tavilyStatus === true ? '已连接' : tavilyStatus === false ? '连接失败' : '测试连接'}
              </Button>
              
              {tavilyStatus === true && (
                <span style={{ fontSize: 12, color: '#10b981' }}>
                  ✓ Tavily API 已配置成功
                </span>
              )}
            </div>
          </Form>
        </Card>
        
        {/* 保存按钮 */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12 }}>
          <Button
            onClick={fetchSettings}
            icon={<ReloadOutlined />}
            style={{ borderRadius: 10 }}
          >
            重置
          </Button>
          <Button
            type="primary"
            onClick={handleSave}
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

        {/* 联网模式说明 */}
        <Card 
          style={{ marginTop: 20, borderRadius: 16, background: 'rgba(99,102,241,0.02)' }}
          title={
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <InfoCircleOutlined style={{ color: '#6366f1' }} />
              <span style={{ fontWeight: 600, color: '#6366f1' }}>联网模式说明</span>
            </div>
          }
        >
          <div style={{ fontSize: 13, color: '#475569', lineHeight: 1.8 }}>
            <div style={{ marginBottom: 12 }}>
              <strong style={{ color: '#1e293b' }}>不联网（默认）</strong>
              <p style={{ margin: '4px 0 0 0' }}>AI 仅使用内置知识回答问题，适合一般学习问题。</p>
            </div>
            <Divider style={{ margin: '12px 0' }} />
            <div style={{ marginBottom: 12 }}>
              <strong style={{ color: '#1e293b' }}>自动搜索</strong>
              <p style={{ margin: '4px 0 0 0' }}>AI 会根据问题自动判断是否需要联网，适合复杂或时效性问题。</p>
            </div>
            <Divider style={{ margin: '12px 0' }} />
            <div style={{ marginBottom: 0 }}>
              <strong style={{ color: '#1e293b' }}>联网搜索</strong>
              <p style={{ margin: '4px 0 0 0' }}>每次回答前都会联网搜索最新信息，适合需要最新资讯的问题。</p>
            </div>
          </div>
        </Card>
      </motion.div>
    </div>
  )
}

export default Settings
