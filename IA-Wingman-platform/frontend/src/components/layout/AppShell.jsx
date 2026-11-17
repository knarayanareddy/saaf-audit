import { useLocation } from 'react-router-dom'
import LeftSidebar from './LeftSidebar'
import IdentityPicker from './IdentityPicker'
import Toast from '../ui/Toast'
import AIChatPanel from '../ai/AIChatPanel'
import ErrorBoundary from '../ErrorBoundary'
import ConfigBanner from './ConfigBanner'
import CommandPalette from '../palette/CommandPalette'
import CreateEngagementModal from '../engagement/CreateEngagementModal'
import { useStore } from '../../store/useStore'

export default function AppShell({ children }) {
  const currentUser = useStore((s) => s.currentUser)
  const authReady = useStore((s) => s.authReady)
  const createEngagementOpen = useStore((s) => s.createEngagementOpen)
  const setCreateEngagementOpen = useStore((s) => s.setCreateEngagementOpen)
  const location = useLocation()

  if (!currentUser || !authReady) return <IdentityPicker />

  return (
    <div className="flex h-screen overflow-hidden">
      <LeftSidebar />
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <ConfigBanner />
        <main className="flex-1 overflow-y-auto">
          {/* Keyed by pathname so navigating to another page clears a caught error */}
          <ErrorBoundary key={location.pathname}>{children}</ErrorBoundary>
        </main>
      </div>
      <AIChatPanel />
      <CommandPalette />
      <CreateEngagementModal open={createEngagementOpen} onClose={() => setCreateEngagementOpen(false)} />
      <Toast />
    </div>
  )
}
