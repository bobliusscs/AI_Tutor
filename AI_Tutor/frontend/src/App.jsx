import { Routes, Route, Navigate } from 'react-router-dom'
import LandingPage from './pages/LandingPage'
import Login from './pages/Login'
import Register from './pages/Register'
import GoalList from './pages/GoalList'
import MainLayout from './layouts/MainLayout'
import GoalKnowledgeGraph from './pages/goal/KnowledgeGraph'
import GoalLearningPlan from './pages/goal/LearningPlan'
import GoalAnalysis from './pages/goal/Analysis'
import GoalMaterials from './pages/goal/Materials'
import GoalQuestions from './pages/goal/Questions'
import GoalChatHistory from './pages/goal/ChatHistory'
import Chat from './pages/Chat'
import Settings from './pages/Settings'
import SkillManagement from './pages/SkillManagement'
import { ErrorBoundary } from './components/ErrorBoundary'
import { PageTransition } from './components/PageTransition'

function App() {
  return (
    <ErrorBoundary>
      <PageTransition>
        <Routes>
          {/* 公开路由 - 无侧边栏 */}
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          
          {/* AI Tutor 核心功能 - 独立入口 */}
          <Route path="/ai-tutor" element={<MainLayout />}>
            <Route index element={<Chat />} />
          </Route>
          
          {/* 设置页面 */}
          <Route path="/settings" element={<Settings />} />

          {/* Skill管理页面 */}
          <Route path="/skills" element={<SkillManagement />} />
          
          {/* 学习目标管理 - 重定向到 AI Tutor */}
          <Route path="/goals" element={<Navigate to="/ai-tutor" replace />} />
          
          {/* 学习目标详情页 */}
          <Route path="/goals/:goalId" element={<MainLayout />}>
            <Route index element={<Navigate to="knowledge-graph" replace />} />
            <Route path="knowledge-graph" element={<GoalKnowledgeGraph />} />
            <Route path="learning-plan" element={<GoalLearningPlan />} />
            <Route path="analysis" element={<GoalAnalysis />} />
            <Route path="materials" element={<GoalMaterials />} />
            <Route path="questions" element={<GoalQuestions />} />
            <Route path="chat" element={<GoalChatHistory />} />
          </Route>
          
          {/* 默认跳转 - 重定向到 AI Tutor */}
          <Route path="*" element={<Navigate to="/ai-tutor" replace />} />
        </Routes>
      </PageTransition>
    </ErrorBoundary>
  )
}

export default App
