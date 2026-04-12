export function Spinner({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="spinner-wrap">
      <div className="spinner" />
      <span>{label}</span>
    </div>
  )
}

export function ErrorMessage({ message }: { message: string }) {
  return <div className="error-box">Error: {message}</div>
}
