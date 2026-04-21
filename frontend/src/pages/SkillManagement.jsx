import { useState, useEffect } from 'react'
import { Card, Button, Tabs, Tag, Popconfirm, Badge, Spin, Empty, Tooltip, message } from 'antd'
import {
  AppstoreOutlined,
  DeleteOutlined,
  DownloadOutlined,
  LockOutlined,
  ReloadOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { skillAPI } from '../utils/api'

function SkillManagement() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [installedSkills, setInstalledSkills] = useState([])
  const [availableSkills, setAvailableSkills] = useState([])
  const [installingSkill, setInstallingSkill] = useState(null)
  const [uninstallingSkill, setUninstallingSkill] = useState(null)

  useEffect(() => {
    fetchSkills()
  }, [])

  // 获取Skills数据
  const fetchSkills = async () => {
    setLoading(true)
    try {
      const [installedRes, availableRes] = await Promise.all([
        skillAPI.listInstalled(),
        skillAPI.getAvailable(),
      ])

      if (installedRes.data.success) {
        setInstalledSkills(installedRes.data.data.skills || [])
      }
      if (availableRes.data.success) {
        setAvailableSkills(availableRes.data.data.skills || [])
      }
    } catch (error) {
      console.error('获取Skills失败:', error)
      message.error('获取Skills失败')
    } finally {
      setLoading(false)
    }
  }

  // 安装Skill
  const handleInstallSkill = async (skillId) => {
    setInstallingSkill(skillId)
    try {
      const response = await skillAPI.install(skillId)
      if (response.data.success) {
        message.success(response.data.message || '安装成功')
        fetchSkills()
      } else {
        message.error(response.data.message || '安装失败')
      }
    } catch (error) {
      message.error('安装失败，请重试')
    } finally {
      setInstallingSkill(null)
    }
  }

  // 卸载Skill
  const handleUninstallSkill = async (skillName) => {
    setUninstallingSkill(skillName)
    try {
      const response = await skillAPI.uninstall(skillName)
      if (response.data.success) {
        message.success(response.data.message || '卸载成功')
        fetchSkills()
      } else {
        message.error(response.data.message || '卸载失败')
      }
    } catch (error) {
      message.error('卸载失败，请重试')
    } finally {
      setUninstallingSkill(null)
    }
  }

  // 渲染已安装Skill卡片
  const renderInstalledCard = (skill) => (
    <motion.div
      key={skill.id}
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      style={{
        padding: '18px 20px',
        borderRadius: 14,
        background: 'rgba(241,245,249,0.85)',
        border: '1.5px solid rgba(226,232,240,0.8)',
        transition: 'all 0.2s',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
            <span style={{ fontSize: 15, fontWeight: 600, color: '#1e293b' }}>
              {skill.name}
            </span>
            {skill.builtin && (
              <Tag color="gold" icon={<LockOutlined />} style={{ fontSize: 11 }}>
                内置
              </Tag>
            )}
            {skill.category === 'subject' && (
              <Tag color="cyan" style={{ fontSize: 11 }}>
                专项
              </Tag>
            )}
            {skill.category === 'learning' && (
              <Tag color="geekblue" style={{ fontSize: 11 }}>
                学习
              </Tag>
            )}
            {skill.category === 'core' && (
              <Tag color="purple" style={{ fontSize: 11 }}>
                核心
              </Tag>
            )}
          </div>
          <div style={{ fontSize: 13, color: '#64748b', lineHeight: 1.5, marginBottom: 10 }}>
            {skill.description?.slice(0, 80) || '无描述'}
            {(skill.description?.length || 0) > 80 ? '...' : ''}
          </div>
          <div style={{ fontSize: 11, color: '#94a3b8' }}>
            版本 {skill.version || '1.0'}
            {skill.installed_at && ` · 安装于 ${new Date(skill.installed_at).toLocaleDateString()}`}
          </div>
        </div>
      </div>
      <div style={{ marginTop: 14, display: 'flex', justifyContent: 'flex-end' }}>
        {skill.builtin ? (
          <Tooltip title="内置Skill无法卸载">
            <Tag icon={<LockOutlined />} style={{ cursor: 'not-allowed' }}>
              不可卸载
            </Tag>
          </Tooltip>
        ) : (
          <Popconfirm
            title="确认卸载"
            description={`确定要卸载 "${skill.name}" 吗？`}
            onConfirm={() => handleUninstallSkill(skill.id)}
            okText="确认"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Button
              type="text"
              danger
              size="small"
              icon={<DeleteOutlined />}
              loading={uninstallingSkill === skill.id}
            >
              卸载
            </Button>
          </Popconfirm>
        )}
      </div>
    </motion.div>
  )

  // 渲染可安装Skill卡片
  const renderAvailableCard = (skill) => (
    <motion.div
      key={skill.id}
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      style={{
        padding: '18px 20px',
        borderRadius: 14,
        background: 'rgba(82,196,26,0.03)',
        border: '1.5px dashed rgba(82,196,26,0.3)',
        transition: 'all 0.2s',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
            <span style={{ fontSize: 15, fontWeight: 600, color: '#1e293b' }}>
              {skill.name}
            </span>
            {skill.category === 'subject' && (
              <Tag color="cyan" style={{ fontSize: 11 }}>
                专项
              </Tag>
            )}
            {skill.category === 'learning' && (
              <Tag color="geekblue" style={{ fontSize: 11 }}>
                学习
              </Tag>
            )}
            {skill.builtin && (
              <Tag color="gold" icon={<LockOutlined />} style={{ fontSize: 11 }}>
                内置
              </Tag>
            )}
          </div>
          <div style={{ fontSize: 13, color: '#64748b', lineHeight: 1.5, marginBottom: 10 }}>
            {skill.description?.slice(0, 100) || '无描述'}
            {(skill.description?.length || 0) > 100 ? '...' : ''}
          </div>
          <div style={{ fontSize: 11, color: '#94a3b8' }}>
            版本 {skill.version || '1.0'}
          </div>
        </div>
      </div>
      <div style={{ marginTop: 14, display: 'flex', justifyContent: 'flex-end' }}>
        <Button
          type="primary"
          size="small"
          icon={<DownloadOutlined />}
          onClick={() => handleInstallSkill(skill.id)}
          loading={installingSkill === skill.id}
          style={{
            background: 'linear-gradient(135deg, #52c41a, #73d13d)',
            border: 'none',
          }}
        >
          安装
        </Button>
      </div>
    </motion.div>
  )

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto' }}>
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
          ← 返回
        </button>

        <div style={{ marginBottom: 24 }}>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: '#1e293b', marginBottom: 8 }}>
            Skill 管理
          </h1>
          <p style={{ color: '#64748b', fontSize: 14 }}>
            管理AI Tutor的功能模块，安装或卸载Skill来扩展系统能力
          </p>
        </div>

        <Card
          style={{ borderRadius: 16 }}
          extra={
            <Button
              icon={<ReloadOutlined />}
              onClick={fetchSkills}
              loading={loading}
            >
              刷新
            </Button>
          }
        >
          <Spin spinning={loading} tip="加载中...">
            <Tabs
              defaultActiveKey="installed"
              size="large"
              items={[
                {
                  key: 'installed',
                  label: (
                    <span style={{ fontSize: 14 }}>
                      <Badge count={installedSkills.length} offset={[8, 0]} style={{ backgroundColor: '#6366f1' }}>
                        已安装
                      </Badge>
                    </span>
                  ),
                  children: (
                    <div style={{ minHeight: 200 }}>
                      {installedSkills.length === 0 ? (
                        <Empty
                          image={Empty.PRESENTED_IMAGE_SIMPLE}
                          description="暂无已安装的Skill"
                          style={{ padding: 40 }}
                        />
                      ) : (
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16 }}>
                          {installedSkills.map(renderInstalledCard)}
                        </div>
                      )}
                    </div>
                  ),
                },
                {
                  key: 'available',
                  label: (
                    <span style={{ fontSize: 14 }}>
                      <Badge count={availableSkills.length} offset={[8, 0]} style={{ backgroundColor: '#52c41a' }}>
                        可安装
                      </Badge>
                    </span>
                  ),
                  children: (
                    <div style={{ minHeight: 200 }}>
                      {availableSkills.length === 0 ? (
                        <Empty
                          image={Empty.PRESENTED_IMAGE_SIMPLE}
                          description="已安装所有可用Skill"
                          style={{ padding: 40 }}
                        />
                      ) : (
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16 }}>
                          {availableSkills.map(renderAvailableCard)}
                        </div>
                      )}
                    </div>
                  ),
                },
              ]}
            />
          </Spin>

          <div style={{ marginTop: 20, padding: '14px 18px', background: 'rgba(99,102,241,0.05)', borderRadius: 12 }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
              <InfoCircleOutlined style={{ color: '#6366f1', marginTop: 2, fontSize: 16 }} />
              <div style={{ fontSize: 13, color: '#475569', lineHeight: 1.7 }}>
                <strong>Skill 说明</strong>
                <ul style={{ margin: '8px 0 0 0', paddingLeft: 18 }}>
                  <li>核心Skill（课件交付、习题交付）为系统内置功能，无法卸载</li>
                  <li>学习Skill（学习交互、学习计划等）和专项Skill（数学、英语等）为扩展模块，可按需安装和卸载</li>
                  <li>安装/卸载Skill后，新会话将自动使用更新后的Skill配置</li>
                </ul>
              </div>
            </div>
          </div>
        </Card>
      </motion.div>
    </div>
  )
}

export default SkillManagement
