import axios from 'axios'

// 创建 axios 实例
const apiClient = axios.create({
  baseURL: '/api',
  // 无超时限制，配合流式输出使用
  headers: {
    'Content-Type': 'application/json',
  },
  // 禁用代理，避免Privoxy干扰
  proxy: false
})

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 添加认证 token
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    // 如果是FormData，自动删除Content-Type让浏览器自动设置
    if (config.data instanceof FormData) {
      delete config.headers['Content-Type']
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    // 返回完整的response，让调用方处理data
    return response
  },
  (error) => {
    console.error('API Error:', error)
    // 处理401未授权错误
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('student_id')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default apiClient

// ============ 认证相关 API ============
export const authAPI = {
  register: (data) => apiClient.post('/student/register', data),
  login: (data) => apiClient.post('/student/login', data),
}

// ============ 聊天 API ============
export const chatAPI = {
  sendMessage: (data) => apiClient.post('/chat/message', data),
  getWelcome: () => apiClient.get('/chat/welcome'),
}

// ============ 知识图谱 API ============
export const knowledgeGraphAPI = {
  generate: (data) => apiClient.post('/knowledge-graph/generate', data),
  // 基于学习目标生成知识图谱（分层生成）
  generateFromGoal: (goalId) => apiClient.post(`/knowledge-graph/goal/${goalId}/generate`),
  // 基于学习目标生成知识图谱（SSE流式版本）
  generateFromGoalStream: (goalId) => {
    const token = localStorage.getItem('token')
    return fetch(`/api/knowledge-graph/goal/${goalId}/generate/stream`, {
      method: 'POST',
      headers: {
        'Authorization': token ? `Bearer ${token}` : '',
        'Content-Type': 'application/json',
      },
      credentials: 'include',
    })
  },
  generateFromMaterialsStream: (goalId, materialIds = null) => {
    // SSE流式生成知识图谱
    const token = localStorage.getItem('token')
    const params = materialIds ? `?material_ids=${materialIds.join(',')}` : ''
    return fetch(`/api/knowledge-graph/goal/${goalId}/generate-from-materials/stream${params}`, {
      method: 'POST',
      headers: {
        'Authorization': token ? `Bearer ${token}` : '',
        'Content-Type': 'application/json',
      },
    })
  },
  cancelGeneration: () => apiClient.post('/knowledge-graph/cancel-generation'),
  get: (id) => apiClient.get(`/knowledge-graph/${id}`),
  visualize: (id) => apiClient.get(`/knowledge-graph/${id}/visualize`),
  // 基于学习目标的路由
  visualizeByGoal: (goalId) => apiClient.get(`/knowledge-graph/goal/${goalId}/visualize`),
  submitAssessment: (goalId, assessments) => apiClient.post(`/knowledge-graph/goal/${goalId}/assess`, assessments),
  getNodeMastery: (goalId, nodeId) => apiClient.get(`/knowledge-graph/goal/${goalId}/nodes/${nodeId}/mastery`),
}

// ============ 学习计划 API（增强超时配置） ============
const pptRequestConfig = {
  timeout: 300000,  // PPT生成请求超时5分钟
  proxy: false
}

export const learningPlanAPI = {
  generate: (data) => apiClient.post('/learning-plan/generate', data),
  generateChaptered: (data) => apiClient.post('/learning-plan/generate-chaptered', data),
  // 取消学习计划生成
  cancelGeneration: () => apiClient.post('/learning-plan/cancel-generation'),
  // SSE流式生成学习计划（带进度）
  generateChapteredStream: (data, onProgress, onComplete, onError, onCancel) => {
    const token = localStorage.getItem('token')
    const url = '/api/learning-plan/generate-chaptered-stream'
    
    fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : ''
      },
      body: JSON.stringify(data)
    })
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      
      function read() {
        reader.read().then(({ done, value }) => {
          if (done) return
          
          const chunk = decoder.decode(value)
          const lines = chunk.split('\n')
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.substring(6))
                
                if (data.type === 'progress') {
                  onProgress && onProgress(data.progress, data.message)
                } else if (data.type === 'complete') {
                  onComplete && onComplete(data.data)
                } else if (data.type === 'cancelled') {
                  onCancel && onCancel(data.message || '用户取消了生成')
                } else if (data.type === 'error') {
                  onError && onError(data.message)
                }
              } catch (e) {
                console.error('解析SSE数据失败:', e)
              }
            }
          }
          
          read()
        })
      }
      
      read()
    })
    .catch(error => {
      onError && onError(error.message)
    })
  },
  // PPT流式生成（带进度）
  generateSectionPPTStream: (sectionId, onProgress, onComplete, onError, onCancel) => {
    const token = localStorage.getItem('token')
    const url = `/api/learning-plan/section/${sectionId}/generate-ppt-stream`
    
    fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : ''
      }
    })
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      
      function read() {
        reader.read().then(({ done, value }) => {
          if (done) return
          
          const chunk = decoder.decode(value)
          const lines = chunk.split('\n')
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.substring(6))
                
                if (data.type === 'progress') {
                  onProgress && onProgress(data.progress, data.message)
                } else if (data.type === 'complete') {
                  onComplete && onComplete(data.data)
                } else if (data.type === 'cancelled') {
                  onCancel && onCancel(data.message || '用户取消了生成')
                } else if (data.type === 'error') {
                  onError && onError(data.message)
                }
              } catch (e) {
                console.error('解析SSE数据失败:', e)
              }
            }
          }
          
          read()
        })
      }
      
      read()
    })
    .catch(error => {
      onError && onError(error.message)
    })
  },
  delete: (id) => apiClient.delete(`/learning-plan/${id}`),
  get: (id) => apiClient.get(`/learning-plan/${id}`),
  getLessons: (id) => apiClient.get(`/learning-plan/${id}/lessons`),
  getNextLesson: (id) => apiClient.get(`/learning-plan/${id}/next-lesson`),
  completeLesson: (id) => apiClient.post('/learning-plan/lesson/${id}/complete'),
  // 重置学习进度
  resetProgress: (id) => apiClient.post(`/learning-plan/${id}/reset-progress`),
  // 章-节结构相关API
  getPlanStructure: (id) => apiClient.get(`/learning-plan/${id}/structure`),
  getChapters: (id) => apiClient.get(`/learning-plan/${id}/chapters`),
  getChapterSections: (chapterId) => apiClient.get(`/learning-plan/chapter/${chapterId}/sections`),
  getChapterPPT: (chapterId) => apiClient.get(`/learning-plan/chapter/${chapterId}/ppt`),
  generateChapterPPT: (chapterId) => apiClient.post(`/learning-plan/chapter/${chapterId}/generate-ppt`, null, pptRequestConfig),
  getSectionPPT: (sectionId) => apiClient.get(`/learning-plan/section/${sectionId}/ppt`),
  // PPT生成使用独立配置，添加超时控制
  generateSectionPPT: (sectionId) => apiClient.post(`/learning-plan/section/${sectionId}/generate-ppt`, null, pptRequestConfig),
}

export const lessonAPI = {
  get: (id) => apiClient.get(`/lesson/${id}`),
  getContent: (id, section = 'all') => apiClient.get(`/lesson/${id}/content?section=${section}`),
}

export const assessmentAPI = {
  generate: (data) => apiClient.post('/assessment/generate', data),
  submit: (data) => apiClient.post('/assessment/submit', data),
}

export const questionAPI = {
  list: (goalId, params) => apiClient.get(`/questions/${goalId}`, { params }),
  generate: (goalId, data) => apiClient.post(`/questions/${goalId}/generate`, data),
  cancelGeneration: () => apiClient.post('/questions/cancel-generation'),
  submit: (goalId, questionId, answer) => apiClient.post(`/questions/${goalId}/submit`, null, {
    params: { question_id: questionId, answer }
  }),
  getPractice: (goalId, count = 10) => apiClient.get(`/questions/${goalId}/practice`, { params: { count } }),
  getWrongQuestions: (goalId) => apiClient.get(`/questions/${goalId}/wrong-questions`),
  delete: (goalId, questionId) => apiClient.delete(`/questions/${goalId}/${questionId}`),
  getKnowledgePoints: (goalId) => apiClient.get(`/questions/${goalId}/knowledge-points`),
  export: (goalId, params) => apiClient.get(`/questions/${goalId}/export`, { params }),
  // 习题上传相关API
  upload: (goalId, data) => apiClient.post(`/questions/${goalId}/upload`, data),
  batchUpload: (goalId, data) => apiClient.post(`/questions/${goalId}/upload/batch`, data),
  parseFromFile: (goalId, formData) => apiClient.post(`/questions/${goalId}/upload/parse`, formData),
  confirmParsed: (goalId, data) => apiClient.post(`/questions/${goalId}/upload/parse-confirm`, data),
  // 个性化练习API
  getPersonalizedPractice: (goalId, count = 10) =>
    apiClient.get(`/questions/${goalId}/personalized-practice`, { params: { count } }),
}

// ============ 练习巩固 API ============
export const practiceAPI = {
  // 获取当前学习位置的小节
  getCurrentSection: (goalId) => 
    apiClient.get(`/practice/${goalId}/current-section`),
  
  // 获取小节练习题（自适应难度）
  getSectionExercises: (goalId, sectionId) => 
    apiClient.get(`/practice/${goalId}/section/${sectionId}/exercises`),
  
  // 提交练习结果
  submitResults: (goalId, data) => 
    apiClient.post(`/practice/${goalId}/submit`, data),
  
  // 获取知识点推荐难度
  getNodeDifficulty: (goalId, nodeId) => 
    apiClient.get(`/practice/${goalId}/node/${nodeId}/difficulty`),
  
  // 标记课时完成（需要用户主动确认）
  markLessonComplete: (lessonId) => 
    apiClient.post(`/learning-plan/lesson/${lessonId}/complete`),
}

export const memoryAPI = {
  getSchedule: (days = 7) => apiClient.get(`/memory/schedule?days=${days}`),
  getStatistics: () => apiClient.get('/memory/statistics'),
  getLearningStyle: () => apiClient.get('/memory/learning-style'),
  updateLearningStyle: (data) => apiClient.put('/memory/learning-style', data),
  getLearningSummary: () => apiClient.get('/memory/learning-summary'),
}

// ============ 学习目标 API ============
export const studyGoalAPI = {
  list: () => apiClient.get('/study-goals/'),
  get: (goalId) => apiClient.get(`/study-goals/${goalId}`),
  create: (data) => apiClient.post('/study-goals/', null, { params: data }),
  update: (goalId, data) => apiClient.put(`/study-goals/${goalId}`, null, { params: data }),
  delete: (goalId) => apiClient.delete(`/study-goals/${goalId}`),
  getProgress: (goalId) => apiClient.get(`/study-goals/${goalId}/progress`),
  getRecords: (goalId) => apiClient.get(`/study-goals/${goalId}/records`),  // 获取学习记录
  deleteRecord: (goalId, recordId) => apiClient.delete(`/study-goals/${goalId}/records/${recordId}`),  // 删除学习记录
  saveSession: (goalId, data) => apiClient.post(`/study-goals/${goalId}/session/save`, data),  // 保存学习会话（前端直接调用）
  generateSummary: (goalId, data) => apiClient.post(`/study-goals/${goalId}/session/generate-summary`, data),  // 调用LLM生成个性化摘要
  getSessionConversation: async (goalId, sessionId) => {
    // 获取学习记录，在其中查找指定 sessionId 的对话记录
    try {
      const res = await apiClient.get(`/study-goals/${goalId}/records`)
      console.log(`[API] 获取学习记录响应:`, res.data)
      
      if (res.data?.success && res.data?.data?.records) {
        const records = res.data.data.records
        console.log(`[API] 找到 ${records.length} 条学习记录`)
        
        for (const record of records) {
          console.log(`[API] 检查记录 ${record.id}, conversations:`, record.conversations)
          
          // 后端返回的是 conversations 字段（不是 conversation_log）
          if (record.conversations && Array.isArray(record.conversations)) {
            console.log(`[API] 在记录 ${record.id} 中查找 session_id=${sessionId}`)
            
            const conversation = record.conversations.find(c => c.session_id === sessionId)
            console.log(`[API] 找到的 conversation:`, conversation)
            
            if (conversation && conversation.messages) {
              console.log(`[API] 找到 ${conversation.messages.length} 条对话消息`)
              return { data: { success: true, conversation: conversation.messages } }
            }
          }
        }
        console.warn(`[API] 未找到 session_id=${sessionId} 的会话记录`)
      }
    } catch (err) {
      console.error('[API] getSessionConversation 失败:', err)
    }
    return { data: { success: false, conversation: null } }
  },
  
  // 生成个性化摘要并保存学习会话（前端直接调用）
  generateSummaryAndSave: async (goalId, data) => {
    try {
      // 先调用 LLM 生成个性化摘要
      const summaryRes = await apiClient.post(`/study-goals/${goalId}/session/generate-summary`, {
        conversation_log: data.conversation_log,
        goal_title: data.goal_title || '',
      })
      
      let personalizedSummary = '学习记录已保存'
      if (summaryRes.data?.success && summaryRes.data?.data?.summary) {
        personalizedSummary = summaryRes.data.data.summary
        console.log('[API] LLM生成个性化摘要成功:', personalizedSummary)
      } else {
        console.warn('[API] LLM生成摘要失败，使用默认摘要')
      }
      
      // 保存到数据库
      const saveRes = await apiClient.post(`/study-goals/${goalId}/session/save`, {
        conversation_log: data.conversation_log,
        summary: personalizedSummary,
        study_duration_minutes: 0,
        lessons_completed: 0,
      })
      
      if (saveRes.data?.success) {
        // 在返回中标记已保存，避免重复
        return { data: { ...saveRes.data, _前端已保存: true } }
      }
      return saveRes
    } catch (err) {
      console.error('[API] generateSummaryAndSave 失败:', err)
      throw err
    }
  },
}

// ============ 学情分析 API ============
export const analysisAPI = {
  getOverview: (goalId) => apiClient.get(`/analysis/${goalId}/overview`),
  getTrends: (goalId, days = 30) => apiClient.get(`/analysis/${goalId}/trends`, { params: { days } }),
  getWeakPoints: (goalId, limit = 10) => apiClient.get(`/analysis/${goalId}/weak-points`, { params: { limit } }),
  getStatistics: (goalId) => apiClient.get(`/analysis/${goalId}/statistics`),
}

// ============ 学习资料 API ============
export const materialAPI = {
  list: (goalId, type) => apiClient.get(`/materials/${goalId}`, { params: { material_type: type } }),
  create: (goalId, data) => apiClient.post(`/materials/${goalId}`, null, { params: data }),
  upload: (goalId, formData) => apiClient.post(`/materials/${goalId}/upload`, formData),
  get: (goalId, materialId) => apiClient.get(`/materials/${goalId}/${materialId}`),
  delete: (goalId, materialId) => apiClient.delete(`/materials/${goalId}/${materialId}`),
  generate: (goalId, nodeId, format) => apiClient.post(`/materials/${goalId}/generate`, null, { 
    params: { node_id: nodeId, material_format: format } 
  }),
}

// ============ 习题库 API ============
// 注意: questionAPI 已在上面定义（见第240行）

// ============ 设置 API ============
export const settingsAPI = {
  getModelConfig: () => apiClient.get('/settings/model-config'),
  saveModelConfig: (data) => apiClient.post('/settings/model-config', data),
  testModel: (params) => apiClient.post('/settings/test-model', null, { params }),
  testTavily: (apiKey) => apiClient.post('/settings/test-tavily', null, { params: { api_key: apiKey } }),
  testTTS: (params) => apiClient.post('/settings/test-tts', null, { params }),
}

// ============ Skill管理 API ============
export const skillAPI = {
  // 获取已安装的Skills列表
  listInstalled: () => apiClient.get('/skills/list'),
  // 获取预设Skill列表
  getPresets: () => apiClient.get('/skills/presets'),
  // 获取可安装但尚未安装的Skills
  getAvailable: () => apiClient.get('/skills/available'),
  // 获取指定Skill的详细信息
  getDetail: (skillName) => apiClient.get(`/skills/${skillName}`),
  // 安装指定Skill
  install: (skillId) => apiClient.post('/skills/install', { skill_id: skillId }),
  // 卸载指定Skill
  uninstall: (skillName) => apiClient.post('/skills/uninstall', { skill_name: skillName }),
  // 获取内置Skill列表
  listBuiltin: () => apiClient.get('/skills/builtin/list'),
}

// ============ TTS语音合成 API ============
export const ttsAPI = {
  // 获取指定节PPT所有幻灯片的讲解语音
  getSlidesAudio: (sectionId, speaker = null) => {
    const data = {}
    if (speaker) data.speaker = speaker
    return apiClient.post(`/tts/slides-audio/${sectionId}`, data, {
      timeout: 300000, // TTS合成可能较慢，5分钟超时
    })
  },
  // TTS服务健康检查
  healthCheck: () => apiClient.get('/tts/health'),
  // 获取单个幻灯片的讲解语音（用于实时播放模式）
  getSingleSlideAudio: (sectionId, slideIndex, speaker = null) => {
    const params = {}
    if (speaker) params.speaker = speaker
    return apiClient.get(`/tts/slide-audio/${sectionId}/${slideIndex}`, {
      params,
      timeout: 120000, // 单页TTS合成超时2分钟
    })
  },
  // 批量合成所有幻灯片语音（SSE流式）
  synthesizeAllAudio: async (sectionId, speaker = null, onProgress) => {
    const url = `${apiClient.defaults.baseURL}/tts/synthesize-all/${sectionId}`
    const data = {}
    if (speaker) data.speaker = speaker
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`,
      },
      body: JSON.stringify(data),
    })
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const dataStr = line.slice(6)
          try {
            const data = JSON.parse(dataStr)
            if (onProgress) {
              onProgress(data)
            }
            
            if (data.type === 'complete') {
              return data
            }
            if (data.type === 'error') {
              throw new Error(data.message)
            }
          } catch (e) {
            // SyntaxError 是 JSON 解析失败，只打印日志
            // 其他错误是业务错误，需要向上传播
            if (e instanceof SyntaxError) {
              console.error('解析SSE数据失败:', e, dataStr)
            } else {
              throw e
            }
          }
        }
      }
    }
  },
  // 合成指定文本的语音（用于AI回复自动朗读）
  synthesizeText: (text, speaker = null) => {
    const data = { text }
    if (speaker) data.speaker = speaker
    return apiClient.post('/tts/synthesize-text', data, {
      timeout: 60000  // 1分钟超时
    })
  },
  // 一键合成章节所有小节的PPT音频（SSE流式）
  synthesizeChapterAudio: async (chapterId, speaker = null, onProgress) => {
    const url = `${apiClient.defaults.baseURL}/tts/synthesize-chapter/${chapterId}`
    const data = {}
    if (speaker) data.speaker = speaker
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`,
      },
      body: JSON.stringify(data),
    })
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const dataStr = line.slice(6)
          try {
            const data = JSON.parse(dataStr)
            if (onProgress) {
              onProgress(data)
            }
            
            if (data.type === 'complete') {
              return data
            }
            if (data.type === 'error') {
              throw new Error(data.message)
            }
          } catch (e) {
            if (e instanceof SyntaxError) {
              console.error('解析SSE数据失败:', e, dataStr)
            } else {
              throw e
            }
          }
        }
      }
    }
  },
}
