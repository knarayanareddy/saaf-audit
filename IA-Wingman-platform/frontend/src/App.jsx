import { lazy, Suspense } from 'react'
import { Routes, Route, useNavigate } from 'react-router-dom'
import { Compass } from 'lucide-react'
import AppShell from './components/layout/AppShell'
import ErrorBoundary from './components/ErrorBoundary'

// Route-level code splitting: the shell loads eagerly, each page is a separate
// chunk fetched on navigation. Keeps the initial bundle small and avoids
// shipping the whole app up front.
const DashboardPage = lazy(() => import('./pages/DashboardPage'))
const EngagementsPage = lazy(() => import('./pages/EngagementsPage'))
const PlanningHubPage = lazy(() => import('./pages/planning/PlanningHubPage'))
const TopicIntelligencePage = lazy(() => import('./pages/planning/TopicIntelligencePage'))
const ProcessUnderstandingPage = lazy(() => import('./pages/planning/ProcessUnderstandingPage'))
const FrameworkRequirementsPage = lazy(() => import('./pages/planning/FrameworkRequirementsPage'))
const SupervisoryGuidancePage = lazy(() => import('./pages/planning/SupervisoryGuidancePage'))
const ScopeObjectivesPage = lazy(() => import('./pages/planning/ScopeObjectivesPage'))
const ANLPage = lazy(() => import('./pages/planning/ANLPage'))
const KickoffPage = lazy(() => import('./pages/planning/KickoffPage'))
const BRAPage = lazy(() => import('./pages/planning/BRAPage'))
const ResourcePlanPage = lazy(() => import('./pages/planning/ResourcePlanPage'))
const WorkProgramPage = lazy(() => import('./pages/planning/WorkProgramPage'))
const DRLPage = lazy(() => import('./pages/planning/DRLPage'))
const RcsaPage = lazy(() => import('./pages/planning/RcsaPage'))
const InterviewPage = lazy(() => import('./pages/planning/InterviewPage'))
const RacmSpinePage = lazy(() => import('./pages/RacmSpinePage'))
const FieldworkPage = lazy(() => import('./pages/FieldworkPage'))
const AgentStudioPage = lazy(() => import('./pages/AgentStudioPage'))
const ReportingHubPage = lazy(() => import('./pages/reporting/ReportingHubPage'))
const QualityHubPage = lazy(() => import('./pages/QualityHubPage'))
const DocumentCenterPage = lazy(() => import('./pages/DocumentCenterPage'))
const AssuranceCenterPage = lazy(() => import('./pages/AssuranceCenterPage'))
const BoardReportPage = lazy(() => import('./pages/BoardReportPage'))
const ShowcasePage = lazy(() => import('./pages/dev/ShowcasePage'))
const WorkflowPage = lazy(() => import('./pages/WorkflowPage'))
const AgentsPage = lazy(() => import('./pages/AgentsPage'))

function RouteFallback() {
  return (
    <div className="mx-auto max-w-5xl px-6 py-8 lg:px-8" aria-busy="true" aria-live="polite">
      <div className="h-8 w-48 animate-pulse rounded-lg bg-surface-3" />
      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-32 animate-pulse rounded-xl bg-surface-3" />)}
      </div>
    </div>
  )
}

function NotFound() {
  const navigate = useNavigate()
  return (
    <div className="mx-auto flex min-h-[60vh] max-w-lg flex-col items-center justify-center px-6 text-center">
      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-subtle text-brand">
        <Compass size={24} />
      </div>
      <h1 className="mt-4 text-h2 text-fg">Page not found</h1>
      <p className="mt-2 text-sm text-fg-muted">
        This page doesn’t exist or may have moved. Let’s get you back on track.
      </p>
      <button
        onClick={() => navigate('/')}
        className="mt-6 rounded-lg bg-brand px-4 py-2 text-sm font-semibold text-brand-fg transition hover:bg-brand-hover"
      >
        Back to dashboard
      </button>
    </div>
  )
}

export default function App() {
  return (
    <AppShell>
      <ErrorBoundary>
        <Suspense fallback={<RouteFallback />}>
          <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/engagements" element={<EngagementsPage />} />
          <Route path="/engagements/:id/planning" element={<PlanningHubPage />} />
          <Route path="/engagements/:id/planning/topic-intelligence" element={<TopicIntelligencePage />} />
          <Route path="/engagements/:id/planning/process-understanding" element={<ProcessUnderstandingPage />} />
          <Route path="/engagements/:id/planning/framework-requirements" element={<FrameworkRequirementsPage />} />
          <Route path="/engagements/:id/planning/supervisory-guidance" element={<SupervisoryGuidancePage />} />
          <Route path="/engagements/:id/planning/scope-objectives" element={<ScopeObjectivesPage />} />
          <Route path="/engagements/:id/planning/anl" element={<ANLPage />} />
          <Route path="/engagements/:id/planning/kickoff" element={<KickoffPage />} />
          <Route path="/engagements/:id/planning/bra" element={<BRAPage />} />
          <Route path="/engagements/:id/planning/resource-plan" element={<ResourcePlanPage />} />
          <Route path="/engagements/:id/planning/work-program" element={<WorkProgramPage />} />
          <Route path="/engagements/:id/planning/drl" element={<DRLPage />} />
          <Route path="/engagements/:id/planning/rcsa" element={<RcsaPage />} />
          <Route path="/engagements/:id/planning/interview" element={<InterviewPage />} />
          <Route path="/engagements/:id/agents" element={<AgentStudioPage />} />
          <Route path="/engagements/:id/reporting" element={<ReportingHubPage />} />
          <Route path="/engagements/:id/quality" element={<QualityHubPage />} />
          <Route path="/engagements/:id/documents" element={<DocumentCenterPage />} />
          <Route path="/assurance" element={<AssuranceCenterPage />} />
          <Route path="/board" element={<BoardReportPage />} />
          <Route path="/workflow" element={<WorkflowPage />} />
          <Route path="/agents" element={<AgentsPage />} />
          <Route path="/engagements/:id/racm" element={<RacmSpinePage />} />
          <Route path="/engagements/:id/fieldwork" element={<FieldworkPage />} />
          <Route path="/dev/showcase" element={<ShowcasePage />} />
          <Route path="*" element={<NotFound />} />
          </Routes>
        </Suspense>
      </ErrorBoundary>
    </AppShell>
  )
}
