import { useState, useEffect } from 'react'
import { Modal, Form, Input, message, Empty, Tabs, Upload, Popconfirm, Spin } from 'antd'
import {
  FileTextOutlined,
  RobotOutlined,
  UserOutlined,
  EyeOutlined,
  DownloadOutlined,
  PlusOutlined,
  DeleteOutlined,
  UploadOutlined,
  PaperClipOutlined,
  FilePdfOutlined,
  FileImageOutlined,
} from '@ant-design/icons'
import { useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { materialAPI } from '../../utils/api'
import apiClient from '../../utils/api'

const { TextArea } = Input
const { Dragger } = Upload

const TYPE_CONFIG = {
  ai_generated:  { label: 'AI生成',   grad: 'linear-gradient(135deg,#8b5cf6,#6366f1)', bg: 'rgba(99,102,241,0.08)',  color: '#6366f1', icon: <RobotOutlined /> },
  user_uploaded: { label: '用户上传', grad: 'linear-gradient(135deg,#06b6d4,#0891b2)', bg: 'rgba(6,182,212,0.08)',   color: '#06b6d4', icon: <UserOutlined /> },
}
const SOURCE_CONFIG = {
  system:   { label: '系统',   bg: 'rgba(99,102,241,0.1)',  color: '#6366f1' },
  user:     { label: '用户',   bg: 'rgba(16,185,129,0.1)',  color: '#10b981' },
  imported: { label: '导入',   bg: 'rgba(245,158,11,0.1)',  color: '#f59e0b' },
}

function Materials() {
  const { goalId } = useParams()
  const [materials, setMaterials]       = useState([])
  const [loading, setLoading]           = useState(true)
  const [isModalOpen, setIsModalOpen]   = useState(false)
  const [isViewModalOpen, setIsViewModalOpen] = useState(false)
  const [selectedMaterial, setSelectedMaterial] = useState(null)
  const [form]                          = Form.useForm()
  const [activeTab, setActiveTab]       = useState('all')
  const [uploadLoading, setUploadLoading] = useState(false)
  const [selectedFile, setSelectedFile] = useState(null)
  
  // 预览相关状态
  const [previewContent, setPreviewContent] = useState(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [previewType, setPreviewType] = useState(null) // 'pdf', 'image', 'text'

  useEffect(() => { fetchMaterials() }, [goalId, activeTab])

  const fetchMaterials = async () => {
    setLoading(true)
    try {
      const type = activeTab === 'all' ? null : activeTab
      const result = await materialAPI.list(goalId, type)
      if (result.data?.success) setMaterials(result.data.data || [])
    } catch { message.error('获取学习资料失败') }
    finally { setLoading(false) }
  }

  // 查看资料详情
  const handleView = async (item) => {
    try {
      const result = await materialAPI.get(goalId, item.id)
      if (result.data?.success) {
        const material = result.data.data
        setSelectedMaterial(material)
        setIsViewModalOpen(true)
        
        // 加载预览内容
        if (material.content_url) {
          loadPreview(material)
        }
      }
    } catch { message.error('获取资料详情失败') }
  }
  
  // 加载预览内容
  const loadPreview = async (material) => {
    if (!material.content_url) return
    
    setPreviewLoading(true)
    setPreviewContent(null)
    setPreviewType(null)
    
    try {
      // 获取当前域名的基础URL（兼容开发和生产环境）
      const baseURL = window.location.origin
      const fileURL = baseURL + material.content_url
      // 从content_url或文件名获取扩展名
      const urlPath = material.content_url || ''
      const fileName = urlPath.split('/').pop() || ''
      const fileExt = fileName.split('.').pop().toLowerCase() || 
                      material.file_format?.toLowerCase() || ''
      
      console.log('[Preview] fileURL:', fileURL, 'fileExt:', fileExt)
      
      // 判断文件类型
      if (fileExt === 'pdf') {
        setPreviewType('pdf')
        setPreviewContent(fileURL)
      } else if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(fileExt)) {
        setPreviewType('image')
        setPreviewContent(fileURL)
      } else if (fileExt === 'txt') {
        setPreviewType('text')
        // 获取文本内容
        const response = await fetch(fileURL)
        if (!response.ok) throw new Error('Failed to fetch text file')
        const text = await response.text()
        setPreviewContent(text)
      } else if (fileExt === 'docx') {
        // Word文档不支持直接预览，提示下载
        setPreviewType('docx')
      } else {
        // 其他类型不支持预览
        setPreviewType('unsupported')
      }
    } catch (error) {
      console.error('预览加载失败:', error)
      setPreviewType('error')
    } finally {
      setPreviewLoading(false)
    }
  }
  
  // 关闭查看弹窗时清理预览状态
  const handleCloseView = () => {
    setIsViewModalOpen(false)
    setSelectedMaterial(null)
    setPreviewContent(null)
    setPreviewType(null)
    setPreviewLoading(false)
  }

  // 删除资料
  const handleDelete = async (item) => {
    try {
      const result = await materialAPI.delete(goalId, item.id)
      if (result.data?.success) {
        message.success('删除成功')
        fetchMaterials()
      }
    } catch { message.error('删除失败') }
  }

  // 下载资料
  const handleDownload = (item) => {
    if (item.content_url) {
      // 打开文件URL进行下载
      const baseURL = apiClient.defaults.baseURL.replace('/api', '')
      const fileURL = baseURL + item.content_url
      window.open(fileURL, '_blank')
    } else if (item.content) {
      // 如果是文本内容，创建下载
      const blob = new Blob([item.content], { type: 'text/plain;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${item.title}.txt`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    }
  }

  // 上传文件
  const handleUpload = async (values) => {
    if (!selectedFile) {
      message.warning('请选择要上传的文件')
      return
    }
    
    setUploadLoading(true)
    try {
      const formData = new FormData()
      formData.append('file', selectedFile)
      formData.append('title', values.title || selectedFile.name)
      formData.append('material_type', 'user_uploaded')
      if (values.description) {
        formData.append('description', values.description)
      }
      
      console.log('[Upload] selectedFile:', selectedFile)
      console.log('[Upload] FormData entries:')
      for (let [key, value] of formData.entries()) {
        console.log(`  ${key}:`, value)
      }
      
      // 不要手动设置Content-Type，axios会自动处理multipart/form-data的boundary
      const result = await apiClient.post(`/materials/${goalId}/upload`, formData)
      
      if (result.data?.success) {
        message.success('文件上传成功')
        setIsModalOpen(false)
        form.resetFields()
        setSelectedFile(null)
        fetchMaterials()
      }
    } catch (error) {
      // 调试：打印完整错误信息
      console.log('Upload error:', error)
      console.log('Error response:', error.response)
      const errorMsg = error.response?.data?.detail || error.response?.data?.message || error.message || '请重试'
      message.error('上传失败: ' + (typeof errorMsg === 'object' ? JSON.stringify(errorMsg) : errorMsg))
    } finally {
      setUploadLoading(false)
    }
  }

  // 创建文本资料（不上传文件）
  const handleCreateText = async (values) => {
    try {
      const result = await materialAPI.create(goalId, { 
        title: values.title, 
        description: values.description, 
        content: values.content, 
        material_type: values.material_type 
      })
      if (result.data?.success) { 
        message.success('资料创建成功'); 
        setIsModalOpen(false); 
        form.resetFields(); 
        fetchMaterials() 
      }
    } catch { message.error('创建失败') }
  }

  // 文件选择处理
  const handleFileChange = (info) => {
    const file = info.file.originFileObj || info.file
    if (file) {
      setSelectedFile(file)
      // 自动填充文件名到标题
      if (!form.getFieldValue('title')) {
        form.setFieldsValue({ title: file.name.replace(/\.[^/.]+$/, '') })
      }
    }
  }

  const tabItems = [
    { key: 'all',          label: '全部' },
    { key: 'ai_generated', label: 'AI生成' },
    { key: 'user_uploaded',label: '用户上传' },
  ]

  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ width: 40, height: 40, borderRadius: 10, background: 'linear-gradient(135deg,#f59e0b,#fb923c)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 4px 12px rgba(245,158,11,0.35)' }}>
            <FileTextOutlined style={{ color: '#fff', fontSize: 18 }} />
          </div>
          <h2 style={{ margin: 0, fontSize: 20, fontWeight: 800, color: '#0f172a' }}>学习资料</h2>
        </div>
        <button onClick={() => setIsModalOpen(true)}
          style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '10px 20px', borderRadius: 10, border: 'none', background: 'linear-gradient(135deg,#6366f1,#8b5cf6)', color: '#fff', fontSize: 13.5, fontWeight: 700, cursor: 'pointer', boxShadow: '0 4px 14px rgba(99,102,241,0.38)', transition: 'all 0.2s' }}>
          <PlusOutlined /> 添加资料
        </button>
      </div>

      {/* Tabs */}
      <div style={{ borderRadius: 20, background: '#fff', border: '1px solid rgba(226,232,240,0.8)', boxShadow: '0 4px 20px rgba(99,102,241,0.06)', overflow: 'hidden' }}>
        <div style={{ padding: '0 20px', borderBottom: '1px solid rgba(226,232,240,0.6)' }}>
          <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
        </div>

        <div style={{ padding: 20 }}>
          {materials.length === 0 ? (
            <Empty description="暂无学习资料">
              <button onClick={() => setIsModalOpen(true)} style={{ padding: '8px 20px', borderRadius: 8, border: 'none', background: 'linear-gradient(135deg,#6366f1,#8b5cf6)', color: '#fff', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
                添加第一份资料
              </button>
            </Empty>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {materials.map((item, idx) => {
                const tc = TYPE_CONFIG[item.material_type] || TYPE_CONFIG.user_uploaded
                const sc = SOURCE_CONFIG[item.source] || { label: item.source, bg: 'rgba(148,163,184,0.1)', color: '#94a3b8' }
                return (
                  <motion.div key={item.id} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35, delay: idx * 0.05 }}
                    whileHover={{ y: -2, boxShadow: '0 8px 32px rgba(99,102,241,0.1)' }}
                    style={{ padding: '18px 20px', borderRadius: 14, background: '#fafbfc', border: '1px solid rgba(226,232,240,0.8)', display: 'flex', alignItems: 'flex-start', gap: 16, transition: 'all 0.2s', cursor: 'default' }}>
                    <div style={{ width: 46, height: 46, borderRadius: 12, background: tc.grad, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 20, color: '#fff', flexShrink: 0, boxShadow: `0 4px 12px ${tc.color}44` }}>
                      {tc.icon}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, flexWrap: 'wrap' }}>
                        <span style={{ fontSize: 15, fontWeight: 700, color: '#0f172a' }}>{item.title}</span>
                        <span style={{ padding: '2px 10px', borderRadius: 99, background: tc.bg, color: tc.color, fontSize: 11.5, fontWeight: 700 }}>{tc.label}</span>
                        <span style={{ padding: '2px 10px', borderRadius: 99, background: sc.bg, color: sc.color, fontSize: 11.5, fontWeight: 700 }}>{sc.label}</span>
                      </div>
                      {item.description && <p style={{ margin: '0 0 8px', fontSize: 13.5, color: '#64748b', lineHeight: 1.5 }}>{item.description}</p>}
                      {item.related_nodes?.length > 0 && (
                        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
                          <span style={{ fontSize: 12, color: '#94a3b8' }}>关联:</span>
                          {item.related_nodes.map(n => <span key={n} style={{ padding: '2px 8px', borderRadius: 99, background: 'rgba(99,102,241,0.07)', color: '#6366f1', fontSize: 11.5 }}>{n}</span>)}
                        </div>
                      )}
                    </div>
                    <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
                      <button 
                        onClick={() => handleView(item)}
                        style={{ padding: '6px 14px', borderRadius: 8, border: '1px solid rgba(226,232,240,0.8)', background: '#fff', color: '#6366f1', fontSize: 12.5, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>
                        <EyeOutlined style={{ fontSize: 12 }} /> 查看
                      </button>
                      {(item.content_url || item.content) && (
                        <button 
                          onClick={() => handleDownload(item)}
                          style={{ padding: '6px 14px', borderRadius: 8, border: '1px solid rgba(226,232,240,0.8)', background: '#fff', color: '#64748b', fontSize: 12.5, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>
                          <DownloadOutlined style={{ fontSize: 12 }} /> 下载
                        </button>
                      )}
                      <Popconfirm
                        title="确认删除"
                        description="确定要删除这份资料吗？"
                        onConfirm={() => handleDelete(item)}
                        okText="删除"
                        cancelText="取消"
                        okButtonProps={{ danger: true }}
                      >
                        <button style={{ padding: '6px 14px', borderRadius: 8, border: '1px solid rgba(226,232,240,0.8)', background: '#fff', color: '#ef4444', fontSize: 12.5, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>
                          <DeleteOutlined style={{ fontSize: 12 }} /> 删除
                        </button>
                      </Popconfirm>
                    </div>
                  </motion.div>
                )
              })}
            </div>
          )}
        </div>
      </div>

      {/* Add/Upload Modal */}
      <Modal 
        title={<span style={{ fontWeight: 700, fontSize: 17 }}>添加学习资料</span>} 
        open={isModalOpen}
        onCancel={() => { setIsModalOpen(false); form.resetFields(); setSelectedFile(null) }} 
        footer={null}
        width={600}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="title" label="资料标题" rules={[{ required: true, message: '请输入资料标题' }]}>
            <Input placeholder="输入资料标题" style={{ borderRadius: 8 }} />
          </Form.Item>
          
          <Form.Item label="上传文件">
            <Dragger
              name="file"
              maxCount={1}
              accept=".pdf,.docx,.doc,.jpg,.jpeg,.png,.gif,.txt"
              beforeUpload={() => false}
              onChange={handleFileChange}
              fileList={selectedFile ? [{ uid: '-1', name: selectedFile.name, status: 'done' }] : []}
              onRemove={() => setSelectedFile(null)}
            >
              <p className="ant-upload-drag-icon">
                <UploadOutlined style={{ color: '#6366f1', fontSize: 32 }} />
              </p>
              <p className="ant-upload-text" style={{ fontSize: 14, color: '#64748b' }}>
                点击或拖拽上传文件
              </p>
              <p className="ant-upload-hint" style={{ fontSize: 12, color: '#94a3b8' }}>
                支持 PDF、Word、图片、文本文件，单个文件不超过50MB
              </p>
            </Dragger>
          </Form.Item>
          
          <Form.Item name="description" label="描述">
            <TextArea rows={2} placeholder="描述这份资料..." style={{ borderRadius: 8 }} />
          </Form.Item>
          
          {/* 仅文本内容时显示 */}
          {!selectedFile && (
            <Form.Item name="content" label="笔记内容">
              <TextArea rows={4} placeholder="输入笔记内容或粘贴链接..." style={{ borderRadius: 8 }} />
            </Form.Item>
          )}
          
          <div style={{ display: 'flex', gap: 12, marginTop: 16 }}>
            <button 
              onClick={() => { setIsModalOpen(false); form.resetFields(); setSelectedFile(null) }}
              disabled={uploadLoading}
              style={{ flex: 1, padding: '10px', borderRadius: 8, border: '1px solid rgba(226,232,240,0.8)', background: uploadLoading ? '#f5f5f5' : '#fff', color: '#64748b', fontSize: 14, fontWeight: 600, cursor: uploadLoading ? 'not-allowed' : 'pointer' }}>
              取消
            </button>
            <button 
              onClick={() => {
                form.validateFields().then(values => {
                  if (selectedFile) {
                    handleUpload(values)
                  } else {
                    handleCreateText(values)
                  }
                })
              }}
              disabled={uploadLoading}
              style={{ flex: 2, padding: '10px', borderRadius: 8, border: 'none', background: uploadLoading ? '#a5a5a5' : 'linear-gradient(135deg,#6366f1,#8b5cf6)', color: '#fff', fontSize: 14, fontWeight: 600, cursor: uploadLoading ? 'not-allowed' : 'pointer' }}>
              {uploadLoading ? '上传中...' : (selectedFile ? '上传文件' : '创建笔记')}
            </button>
          </div>
        </Form>
      </Modal>

      {/* View Detail Modal */}
      <Modal
        title={<span style={{ fontWeight: 700, fontSize: 17 }}>查看资料</span>}
        open={isViewModalOpen}
        onCancel={handleCloseView}
        footer={[
          selectedMaterial?.content_url && (
            <button 
              key="download"
              onClick={() => handleDownload(selectedMaterial)}
              style={{ padding: '8px 20px', borderRadius: 8, border: '1px solid rgba(226,232,240,0.8)', background: '#fff', color: '#64748b', fontSize: 13, fontWeight: 600, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
              <DownloadOutlined /> 下载
            </button>
          ),
          <button 
            key="close"
            onClick={handleCloseView}
            style={{ padding: '8px 20px', borderRadius: 8, border: 'none', background: 'linear-gradient(135deg,#6366f1,#8b5cf6)', color: '#fff', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
            关闭
          </button>
        ]}
        width={800}
      >
        {selectedMaterial && (
          <div style={{ padding: '10px 0' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
              <div style={{ 
                width: 48, height: 48, borderRadius: 12, 
                background: TYPE_CONFIG[selectedMaterial.material_type]?.grad || TYPE_CONFIG.user_uploaded.grad,
                display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 22, color: '#fff' 
              }}>
                {TYPE_CONFIG[selectedMaterial.material_type]?.icon || TYPE_CONFIG.user_uploaded.icon}
              </div>
              <div>
                <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: '#0f172a' }}>{selectedMaterial.title}</h3>
                <div style={{ display: 'flex', gap: 8, marginTop: 6 }}>
                  <span style={{ 
                    padding: '2px 10px', borderRadius: 99, 
                    background: TYPE_CONFIG[selectedMaterial.material_type]?.bg || TYPE_CONFIG.user_uploaded.bg, 
                    color: TYPE_CONFIG[selectedMaterial.material_type]?.color || TYPE_CONFIG.user_uploaded.color, 
                    fontSize: 11.5, fontWeight: 700 
                  }}>
                    {TYPE_CONFIG[selectedMaterial.material_type]?.label || '未知'}
                  </span>
                  <span style={{ 
                    padding: '2px 10px', borderRadius: 99, 
                    background: SOURCE_CONFIG[selectedMaterial.source]?.bg || 'rgba(148,163,184,0.1)', 
                    color: SOURCE_CONFIG[selectedMaterial.source]?.color || '#94a3b8', 
                    fontSize: 11.5, fontWeight: 700 
                  }}>
                    {SOURCE_CONFIG[selectedMaterial.source]?.label || selectedMaterial.source}
                  </span>
                </div>
              </div>
            </div>
            
            {selectedMaterial.description && (
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#64748b', marginBottom: 4 }}>描述</div>
                <div style={{ fontSize: 14, color: '#475569', lineHeight: 1.6, padding: '12px 16px', background: '#f8fafc', borderRadius: 8 }}>
                  {selectedMaterial.description}
                </div>
              </div>
            )}
            
            {selectedMaterial.content && !selectedMaterial.content_url && (
              <div>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#64748b', marginBottom: 4 }}>内容</div>
                <div style={{ fontSize: 14, color: '#475569', lineHeight: 1.8, padding: '12px 16px', background: '#f8fafc', borderRadius: 8, maxHeight: 300, overflowY: 'auto', whiteSpace: 'pre-wrap' }}>
                  {selectedMaterial.content}
                </div>
              </div>
            )}
            
            {/* 预览区域 */}
            {selectedMaterial.content_url && (
              <div style={{ marginTop: 16 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#64748b', marginBottom: 8 }}>预览</div>
                
                {previewLoading && (
                  <div style={{ padding: '40px', textAlign: 'center', background: '#f8fafc', borderRadius: 8 }}>
                    <Spin size="large" />
                    <p style={{ marginTop: 12, color: '#64748b' }}>加载预览中...</p>
                  </div>
                )}
                
                {!previewLoading && previewType === 'pdf' && (
                  <div style={{ border: '1px solid rgba(226,232,240,0.8)', borderRadius: 8, overflow: 'hidden' }}>
                    <iframe
                      src={previewContent}
                      style={{ width: '100%', height: '500px', border: 'none' }}
                      title="PDF预览"
                      allowFullScreen
                      loading="lazy"
                    />
                    <div style={{ padding: '12px 16px', background: '#f8fafc', borderTop: '1px solid rgba(226,232,240,0.5)', textAlign: 'center' }}>
                      <a href={previewContent} target="_blank" rel="noopener noreferrer" 
                         style={{ color: '#6366f1', fontSize: 13, textDecoration: 'none' }}>
                        在新窗口打开PDF
                      </a>
                    </div>
                  </div>
                )}
                
                {!previewLoading && previewType === 'docx' && (
                  <div style={{ padding: '40px', textAlign: 'center', background: '#f8fafc', borderRadius: 8 }}>
                    <FileTextOutlined style={{ fontSize: 48, color: '#6366f1' }} />
                    <p style={{ marginTop: 12, color: '#475569', fontSize: 14 }}>Word 文档</p>
                    <p style={{ marginTop: 8, color: '#64748b', fontSize: 13 }}>该文件类型暂不支持在线预览</p>
                    <p style={{ fontSize: 12, color: '#94a3b8' }}>请点击下载按钮查看文档内容</p>
                  </div>
                )}
                
                {!previewLoading && previewType === 'image' && (
                  <div style={{ textAlign: 'center', padding: '20px', background: '#f8fafc', borderRadius: 8 }}>
                    <img
                      src={previewContent}
                      alt={selectedMaterial.title}
                      style={{ maxWidth: '100%', maxHeight: '500px', borderRadius: 4 }}
                    />
                  </div>
                )}
                
                {!previewLoading && previewType === 'text' && (
                  <div style={{ padding: '16px', background: '#f8fafc', borderRadius: 8, maxHeight: '400px', overflowY: 'auto' }}>
                    <pre style={{ margin: 0, fontSize: 14, lineHeight: 1.6, whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontFamily: 'monospace', color: '#334155' }}>
                      {previewContent}
                    </pre>
                  </div>
                )}
                
                {!previewLoading && previewType === 'unsupported' && (
                  <div style={{ padding: '40px', textAlign: 'center', background: '#f8fafc', borderRadius: 8 }}>
                    <FileTextOutlined style={{ fontSize: 48, color: '#94a3b8' }} />
                    <p style={{ marginTop: 12, color: '#64748b' }}>该文件类型暂不支持预览</p>
                    <p style={{ fontSize: 12, color: '#94a3b8' }}>请下载后查看</p>
                  </div>
                )}
                
                {!previewLoading && previewType === 'error' && (
                  <div style={{ padding: '40px', textAlign: 'center', background: '#fef2f2', borderRadius: 8 }}>
                    <p style={{ color: '#ef4444' }}>预览加载失败</p>
                    <p style={{ fontSize: 12, color: '#94a3b8' }}>请尝试下载后查看</p>
                  </div>
                )}
              </div>
            )}
            
            <div style={{ display: 'flex', gap: 16, marginTop: 16, padding: '12px 0', borderTop: '1px solid rgba(226,232,240,0.5)' }}>
              <div style={{ fontSize: 12, color: '#94a3b8' }}>创建时间: {new Date(selectedMaterial.created_at).toLocaleString('zh-CN')}</div>
              <div style={{ fontSize: 12, color: '#94a3b8' }}>查看次数: {selectedMaterial.view_count || 0}</div>
            </div>
          </div>
        )}
      </Modal>
    </motion.div>
  )
}

export default Materials
