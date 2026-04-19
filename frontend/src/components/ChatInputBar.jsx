import { useState, useRef, useCallback, useEffect } from 'react'
import { Tooltip, message } from 'antd'
import {
  PaperClipOutlined,
  PictureOutlined,
  VideoCameraOutlined,
  AudioOutlined,
  SendOutlined,
  StopOutlined,
  CloseOutlined,
  FileOutlined,
  VideoCameraFilled,
  SoundOutlined,
  MutedOutlined,
} from '@ant-design/icons'
import { motion, AnimatePresence } from 'framer-motion'

// ── 工具函数 ────────────────────────────────────────────────────────────────

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function getFileCategory(file) {
  const name = file.name.toLowerCase()
  if (/\.(jpg|jpeg|png|gif|webp)$/.test(name)) return 'image'
  if (/\.(mp4|webm|mov)$/.test(name)) return 'video'
  if (/\.(mp3|wav|ogg|flac|aac|m4a|wma)$/.test(name)) return 'audio'
  return 'file'
}

// ── 附件预览项 ───────────────────────────────────────────────────────────────

function AttachmentItem({ attachment, onRemove }) {
  const isImage = attachment.type === 'image'
  const isVideo = attachment.type === 'video'
  const isAudio = attachment.type === 'audio'

  const containerStyle = {
    position: 'relative',
    flexShrink: 0,
    borderRadius: 10,
    overflow: 'hidden',
    border: '1px solid rgba(226,232,240,0.8)',
    background: '#f8faff',
  }

  const removeBtn = (
    <motion.button
      whileHover={{ scale: 1.15 }}
      whileTap={{ scale: 0.9 }}
      onClick={() => onRemove(attachment.id)}
      style={{
        position: 'absolute',
        top: 3,
        right: 3,
        width: 18,
        height: 18,
        borderRadius: '50%',
        border: 'none',
        background: 'rgba(0,0,0,0.55)',
        color: '#fff',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 0,
        zIndex: 2,
      }}
    >
      <CloseOutlined style={{ fontSize: 9 }} />
    </motion.button>
  )

  if (isImage && attachment.preview) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.8 }}
        style={{ ...containerStyle, width: 60, height: 60 }}
      >
        <img
          src={attachment.preview}
          alt={attachment.name}
          style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
        />
        {removeBtn}
      </motion.div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.8 }}
      style={{ ...containerStyle, display: 'flex', alignItems: 'center', gap: 6, padding: '6px 28px 6px 8px', maxWidth: 160 }}
    >
      {isVideo
        ? <VideoCameraFilled style={{ color: '#6366f1', fontSize: 16, flexShrink: 0 }} />
        : isAudio
          ? <AudioOutlined style={{ color: '#10b981', fontSize: 16, flexShrink: 0 }} />
          : <FileOutlined style={{ color: '#64748b', fontSize: 16, flexShrink: 0 }} />
      }
      <div style={{ overflow: 'hidden', minWidth: 0 }}>
        <div style={{ fontSize: 11.5, fontWeight: 600, color: '#1e293b', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {attachment.name}
        </div>
        <div style={{ fontSize: 10.5, color: '#94a3b8' }}>{formatFileSize(attachment.size)}</div>
      </div>
      {removeBtn}
    </motion.div>
  )
}

// ── 工具栏按钮 ───────────────────────────────────────────────────────────────

function ToolbarBtn({ icon, tooltip, onClick, active, activeStyle, disabled }) {
  const [hovered, setHovered] = useState(false)

  return (
    <Tooltip title={tooltip}>
      <motion.button
        whileHover={disabled ? {} : { scale: 1.1 }}
        whileTap={disabled ? {} : { scale: 0.92 }}
        onClick={disabled ? undefined : onClick}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        style={{
          width: 32,
          height: 32,
          borderRadius: '50%',
          border: 'none',
          cursor: disabled ? 'not-allowed' : 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          transition: 'all 0.15s',
          background: active
            ? (activeStyle?.background ?? 'rgba(239,68,68,1)')
            : hovered
              ? 'rgba(241,245,249,1)'
              : 'transparent',
          color: active
            ? '#fff'
            : hovered ? '#475569' : '#64748b',
          ...(active ? activeStyle : {}),
        }}
      >
        {icon}
      </motion.button>
    </Tooltip>
  )
}

// ── 主组件 ───────────────────────────────────────────────────────────────────

export default function ChatInputBar({
  value = '',
  onChange,
  onSend,
  loading = false,
  stopping = false,
  onStop,
  disabled = false,
  onVoiceInputStart,
  onVoiceInputEnd,
  isVoiceInput: isVoiceInputProp,
  autoReadEnabled = true,
  onAutoReadToggle,
  isPlayingTTS = false,
}) {
  const [attachments, setAttachments] = useState([])
  const [isDragging, setIsDragging] = useState(false)
  const [isRecording, setIsRecording] = useState(false)

  const fileInputRef = useRef(null)
  const imageInputRef = useRef(null)
  const videoInputRef = useRef(null)
  const textareaRef = useRef(null)
  const recognitionRef = useRef(null)
  const dragCounterRef = useRef(0)
  const silenceTimerRef = useRef(null)
  const hasSpeechResultRef = useRef(false)
  const isVoiceInputRef = useRef(false)

  const speechSupported =
    typeof window !== 'undefined' &&
    !!(window.SpeechRecognition || window.webkitSpeechRecognition)

  // ── 清理静默检测定时器 ────────────────────────────────────────────────────
  const clearSilenceTimer = useCallback(() => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current)
      silenceTimerRef.current = null
    }
  }, [])

  // ── 清理 object URLs ──────────────────────────────────────────────────────
  useEffect(() => {
    return () => {
      attachments.forEach(a => {
        if (a.preview) URL.revokeObjectURL(a.preview)
      })
      // 清理静默检测定时器
      clearSilenceTimer()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clearSilenceTimer])

  // ── 添加附件 ──────────────────────────────────────────────────────────────
  const addFiles = useCallback((files) => {
    const newItems = []
    for (const file of files) {
      const type = getFileCategory(file)
      // 大小限制
      if (type === 'video' && file.size > 200 * 1024 * 1024) {
        message.warning(`视频文件 ${file.name} 超过 200MB 限制，已跳过`)
        continue
      }
      if (type === 'file' && file.size > 50 * 1024 * 1024) {
        message.warning(`文件 ${file.name} 超过 50MB 限制，已跳过`)
        continue
      }
      const preview = type === 'image' ? URL.createObjectURL(file) : null
      newItems.push({
        id: `${Date.now()}_${Math.random().toString(36).slice(2)}`,
        file,
        type,
        preview,
        name: file.name,
        size: file.size,
      })
    }
    if (newItems.length > 0) {
      setAttachments(prev => [...prev, ...newItems])
    }
  }, [])

  const removeAttachment = useCallback((id) => {
    setAttachments(prev => {
      const item = prev.find(a => a.id === id)
      if (item?.preview) URL.revokeObjectURL(item.preview)
      return prev.filter(a => a.id !== id)
    })
  }, [])

  // ── 文件输入处理 ──────────────────────────────────────────────────────────
  const handleFileInput = (e) => {
    if (e.target.files?.length) {
      addFiles(Array.from(e.target.files))
      e.target.value = ''
    }
  }

  // ── 粘贴图片 ──────────────────────────────────────────────────────────────
  const handlePaste = useCallback((e) => {
    const items = e.clipboardData?.items
    if (!items) return
    const imageFiles = []
    for (const item of items) {
      if (item.type.startsWith('image/')) {
        const file = item.getAsFile()
        if (file) imageFiles.push(file)
      }
    }
    if (imageFiles.length > 0) {
      addFiles(imageFiles)
    }
  }, [addFiles])

  // ── 拖拽上传 ──────────────────────────────────────────────────────────────
  const handleDragEnter = (e) => {
    e.preventDefault()
    dragCounterRef.current++
    setIsDragging(true)
  }

  const handleDragLeave = (e) => {
    e.preventDefault()
    dragCounterRef.current--
    if (dragCounterRef.current === 0) setIsDragging(false)
  }

  const handleDragOver = (e) => {
    e.preventDefault()
  }

  const handleDrop = (e) => {
    e.preventDefault()
    dragCounterRef.current = 0
    setIsDragging(false)
    const files = Array.from(e.dataTransfer.files)
    if (files.length > 0) addFiles(files)
  }

  // ── 语音输入 ──────────────────────────────────────────────────────────────
  const toggleVoice = useCallback(() => {
    if (!speechSupported) {
      message.warning('您的浏览器不支持语音输入')
      return
    }

    if (isRecording) {
      // 用户主动点击停止，不自动发送
      clearSilenceTimer()
      recognitionRef.current?.stop()
      setIsRecording(false)
      hasSpeechResultRef.current = false
      isVoiceInputRef.current = false
      onVoiceInputEnd?.(false) // false 表示用户主动停止，不自动发送
      return
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    const recognition = new SpeechRecognition()
    recognition.lang = 'zh-CN'
    recognition.continuous = true
    recognition.interimResults = true

    // 标记语音输入开始
    isVoiceInputRef.current = true
    hasSpeechResultRef.current = false
    onVoiceInputStart?.()

    recognition.onresult = (event) => {
      let transcript = ''
      let isFinal = false
      for (let i = event.resultIndex; i < event.results.length; i++) {
        transcript += event.results[i][0].transcript
        if (event.results[i].isFinal) {
          isFinal = true
        }
      }
      
      // 更新输入值
      onChange?.(value + transcript)
      
      // 如果有识别结果，标记为有内容并启动静默检测
      if (transcript.trim()) {
        hasSpeechResultRef.current = true
        
        // 重置静默检测定时器
        clearSilenceTimer()
        silenceTimerRef.current = setTimeout(() => {
          // 1.5秒静默后自动发送
          if (hasSpeechResultRef.current && value.trim()) {
            // 停止语音识别
            recognition.stop()
            setIsRecording(false)
            
            // 触发发送（传递 isVoiceInput 标记）
            onSend?.(value.trim(), [], true)
            onChange?.('')
            
            // 通知父组件语音输入结束（自动发送）
            onVoiceInputEnd?.(true)
            
            // 重置状态
            hasSpeechResultRef.current = false
            isVoiceInputRef.current = false
          }
        }, 1500)
      }
    }

    recognition.onerror = (event) => {
      console.error('[ChatInputBar] Speech recognition error:', event.error)
      clearSilenceTimer()
      setIsRecording(false)
      hasSpeechResultRef.current = false
      isVoiceInputRef.current = false
      onVoiceInputEnd?.(false)
      message.error('语音识别出错，请重试')
    }

    recognition.onend = () => {
      clearSilenceTimer()
      setIsRecording(false)
      // 注意：如果是自动发送导致的 stop，这里不需要额外处理
      // 因为已经在定时器中处理了
    }

    recognition.start()
    recognitionRef.current = recognition
    setIsRecording(true)
  }, [isRecording, speechSupported, onChange, value, onSend, onVoiceInputStart, onVoiceInputEnd, clearSilenceTimer])

  // ── 发送 ─────────────────────────────────────────────────────────────────
  const handleSend = useCallback(() => {
    const text = value.trim()
    if (!text && attachments.length === 0) return
    if (loading || disabled) return

    // 如果是语音输入模式，传递 isVoiceInput 标记
    const isFromVoice = isVoiceInputRef.current
    onSend?.(text, attachments, isFromVoice)
    onChange?.('')
    // 清空附件（revoke已在发送侧或下次 effect 处理）
    setAttachments([])
    // 重置语音输入标记
    isVoiceInputRef.current = false
  }, [value, attachments, loading, disabled, onSend, onChange])

  // ── 键盘 ─────────────────────────────────────────────────────────────────
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (loading) {
        onStop?.()
      } else {
        handleSend()
      }
    }
  }

  const hasContent = value.trim().length > 0 || attachments.length > 0

  // ── 渲染 ─────────────────────────────────────────────────────────────────
  return (
    <div
      style={{ position: 'relative' }}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      {/* 隐藏文件输入 */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".pdf,.docx,.doc,.txt,.csv,.xlsx,.mp3,.wav,.ogg,.flac,.aac,.m4a"
        style={{ display: 'none' }}
        onChange={handleFileInput}
      />
      <input
        ref={imageInputRef}
        type="file"
        multiple
        accept=".jpg,.jpeg,.png,.gif,.webp"
        style={{ display: 'none' }}
        onChange={handleFileInput}
      />
      <input
        ref={videoInputRef}
        type="file"
        multiple
        accept=".mp4,.webm,.mov"
        style={{ display: 'none' }}
        onChange={handleFileInput}
      />

      {/* 主容器 */}
      <div
        style={{
          borderRadius: 24,
          border: isDragging
            ? '2px dashed #6366f1'
            : '1.5px solid rgba(226,232,240,0.9)',
          background: '#fff',
          boxShadow: '0 2px 20px rgba(99,102,241,0.07)',
          overflow: 'hidden',
          transition: 'border-color 0.2s, box-shadow 0.2s',
          boxSizing: 'border-box',
        }}
      >
        {/* 附件预览区 */}
        <AnimatePresence>
          {attachments.length > 0 && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              style={{
                padding: '10px 14px 0',
                display: 'flex',
                flexWrap: 'wrap',
                gap: 8,
              }}
            >
              <AnimatePresence>
                {attachments.map(att => (
                  <AttachmentItem
                    key={att.id}
                    attachment={att}
                    onRemove={removeAttachment}
                  />
                ))}
              </AnimatePresence>
            </motion.div>
          )}
        </AnimatePresence>

        {/* 文本输入区 */}
        <div style={{ padding: '12px 16px 6px' }}>
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => onChange?.(e.target.value)}
            onKeyDown={handleKeyDown}
            onPaste={handlePaste}
            placeholder="输入消息..."
            disabled={disabled}
            rows={1}
            style={{
              width: '100%',
              border: 'none',
              outline: 'none',
              resize: 'none',
              background: 'transparent',
              fontSize: 14.5,
              lineHeight: 1.65,
              color: '#1e293b',
              fontFamily: 'inherit',
              overflowY: 'auto',
              maxHeight: `${6 * 1.65 * 14.5}px`,
              minHeight: `${1 * 1.65 * 14.5}px`,
              boxSizing: 'border-box',
            }}
            onInput={(e) => {
              // 自适应高度
              e.target.style.height = 'auto'
              e.target.style.height = Math.min(e.target.scrollHeight, 6 * 1.65 * 14.5) + 'px'
            }}
          />
        </div>

        {/* 底部工具栏 */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '6px 10px 10px',
        }}>
          {/* 左侧工具按钮 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <ToolbarBtn
              icon={<PaperClipOutlined style={{ fontSize: 15 }} />}
              tooltip="附件（PDF/Word/TXT/CSV/Excel/音频）"
              onClick={() => fileInputRef.current?.click()}
              disabled={disabled}
            />
            <ToolbarBtn
              icon={<PictureOutlined style={{ fontSize: 15 }} />}
              tooltip="图片（JPG/PNG/GIF/WebP）"
              onClick={() => imageInputRef.current?.click()}
              disabled={disabled}
            />
            <ToolbarBtn
              icon={<VideoCameraOutlined style={{ fontSize: 15 }} />}
              tooltip="视频（MP4/WebM/MOV）"
              onClick={() => videoInputRef.current?.click()}
              disabled={disabled}
            />
            <Tooltip title={speechSupported ? (isRecording ? '点击停止录音' : '语音输入') : '您的浏览器不支持语音输入'}>
              <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.92 }}
                onClick={toggleVoice}
                className={isRecording ? 'voice-recording-pulse' : ''}
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: '50%',
                  border: isRecording ? '2px solid #ef4444' : 'none',
                  cursor: speechSupported ? 'pointer' : 'not-allowed',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  transition: 'all 0.15s',
                  background: isRecording ? '#ef4444' : 'transparent',
                  color: isRecording ? '#fff' : '#64748b',
                  boxShadow: isRecording ? '0 0 0 4px rgba(239,68,68,0.2)' : 'none',
                }}
              >
                <AudioOutlined style={{ fontSize: 15 }} />
              </motion.button>
            </Tooltip>
            <ToolbarBtn
              icon={autoReadEnabled ? <SoundOutlined style={{ fontSize: 15 }} /> : <MutedOutlined style={{ fontSize: 15 }} />}
              tooltip={autoReadEnabled ? '自动朗读已开启（语音对话后AI回复自动朗读）' : '自动朗读已关闭'}
              onClick={onAutoReadToggle}
              active={autoReadEnabled}
              activeStyle={{ background: '#6366f1' }}
            />
          </div>

          {/* 右侧发送/停止按钮 */}
          <Tooltip title={loading ? '停止生成' : (hasContent ? '发送消息' : '')}>
            <motion.button
              whileHover={{ scale: 1.07 }}
              whileTap={{ scale: 0.94 }}
              onClick={loading ? onStop : handleSend}
              disabled={!loading && !hasContent}
              style={{
                width: 36,
                height: 36,
                borderRadius: '50%',
                border: 'none',
                cursor: loading || hasContent ? 'pointer' : 'not-allowed',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'all 0.2s',
                flexShrink: 0,
                background: loading
                  ? '#374151'
                  : hasContent
                    ? '#6366f1'
                    : '#f1f5f9',
                boxShadow: loading
                  ? '0 4px 14px rgba(55,65,81,0.25)'
                  : hasContent
                    ? '0 4px 14px rgba(99,102,241,0.3)'
                    : 'none',
              }}
            >
              {loading ? (
                stopping ? (
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 0.8, repeat: Infinity, ease: 'linear' }}
                    style={{
                      width: 16,
                      height: 16,
                      border: '2.5px solid rgba(255,255,255,0.3)',
                      borderTopColor: '#fff',
                      borderRadius: '50%',
                    }}
                  />
                ) : (
                  <StopOutlined style={{ color: '#fff', fontSize: 15 }} />
                )
              ) : (
                <SendOutlined style={{ color: hasContent ? '#fff' : '#94a3b8', fontSize: 15 }} />
              )}
            </motion.button>
          </Tooltip>
        </div>
      </div>

      {/* 拖拽遮罩 */}
      <AnimatePresence>
        {isDragging && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            style={{
              position: 'absolute',
              inset: 0,
              borderRadius: 24,
              background: 'rgba(99,102,241,0.06)',
              border: '2px dashed #6366f1',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 10,
              pointerEvents: 'none',
            }}
          >
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 8,
              color: '#6366f1',
              fontWeight: 600,
              fontSize: 15,
            }}>
              <PaperClipOutlined style={{ fontSize: 28 }} />
              <span>拖放文件到此处</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* CSS */}
      <style>{`
        @keyframes voice-pulse {
          0%, 100% { box-shadow: 0 0 0 0 rgba(239,68,68,0.5); }
          50% { box-shadow: 0 0 0 8px rgba(239,68,68,0); }
        }
        .voice-recording-pulse {
          animation: voice-pulse 1.2s ease-in-out infinite;
        }
        textarea::placeholder {
          color: #b0bec5;
        }
        textarea::-webkit-scrollbar {
          width: 4px;
        }
        textarea::-webkit-scrollbar-track {
          background: transparent;
        }
        textarea::-webkit-scrollbar-thumb {
          background: rgba(148,163,184,0.4);
          border-radius: 2px;
        }
      `}</style>
    </div>
  )
}
