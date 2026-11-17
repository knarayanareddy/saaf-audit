import { Component } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'
import { isStaleBuildError, reloadForNewVersion } from '../lib/staleBuild'

/**
 * Catches rendering errors anywhere in the tree below it and shows a recovery
 * panel instead of a white screen. Critical so one page's bug never takes down
 * the whole application during use or a live demo.
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, info) {
    // A page that could not load because a newer version was deployed is not a
    // bug in the page: reload once and the new version loads (lib/staleBuild.js).
    if (isStaleBuildError(error) && reloadForNewVersion()) return
    // Log to console for developers; never surface stack traces to end users.
    console.error('UI error caught by ErrorBoundary:', error, info)
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (!this.state.hasError) return this.props.children

    if (isStaleBuildError(this.state.error)) {
      return (
        <div className="flex min-h-[60vh] items-center justify-center p-8">
          <div className="border border-line max-w-md rounded-lg bg-surface p-8 text-center">
            <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-brand/10 text-brand">
              <RefreshCw size={22} />
            </div>
            <h1 className="mt-4 text-lg font-semibold text-fg">A new version of IA Wingman is available</h1>
            <p className="mt-2 text-sm text-fg-muted">
              This page belongs to the version you opened earlier. Reload to load the current one; nothing you saved is lost.
            </p>
            <div className="mt-6 flex justify-center">
              <button
                onClick={() => window.location.reload()}
                className="flex items-center gap-2 rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-hover"
              >
                <RefreshCw size={14} /> Reload
              </button>
            </div>
          </div>
        </div>
      )
    }

    return (
      <div className="flex min-h-[60vh] items-center justify-center p-8">
        <div className="border border-line max-w-md rounded-lg bg-surface p-8 text-center">
          <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-sev-med/10 text-sev-med">
            <AlertTriangle size={24} />
          </div>
          <h1 className="mt-4 text-lg font-semibold text-fg">Something went wrong on this page</h1>
          <p className="mt-2 text-sm text-fg-muted">
            The rest of the application is still working. Try reloading this view, or go back to the dashboard.
          </p>
          <div className="mt-6 flex justify-center gap-2">
            <button
              onClick={this.handleReset}
              className="flex items-center gap-2 rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-hover"
            >
              <RefreshCw size={14} /> Try again
            </button>
            <button
              onClick={() => { window.location.href = '/' }}
              className="rounded-lg border border-line px-4 py-2 text-sm text-fg-muted hover:bg-surface-3"
            >
              Go to dashboard
            </button>
          </div>
        </div>
      </div>
    )
  }
}
