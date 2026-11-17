import { createPortal } from 'react-dom'
import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import EditEngagementModal from './EditEngagementModal'
import { getEngagement } from '../../api/engagements'
import { useStore } from '../../store/useStore'

// The edit window for the audit you are working on, openable from any page. The window
// itself was only reachable from the Engagements list, which nobody looks at once they
// are inside an audit. The store keeps only the few fields the sidebar needs, so the
// full record is fetched when the window opens; the sidebar follows the saved result.
export default function EditActiveEngagement({ open, onClose, engagementId }) {
  const setActiveEngagement = useStore((s) => s.setActiveEngagement)
  const { data: engagement } = useQuery({
    queryKey: ['engagement', engagementId],
    queryFn: () => getEngagement(engagementId),
    enabled: open && !!engagementId,
  })

  useEffect(() => {
    if (engagement && engagement.id === engagementId) setActiveEngagement(engagement)
  }, [engagement, engagementId, setActiveEngagement])

  // In the page body, not inside the sidebar that opens it: the sidebar is a narrow column.
  return createPortal(
    <EditEngagementModal open={open} onClose={onClose} engagement={open ? engagement : null} />,
    document.body,
  )
}
