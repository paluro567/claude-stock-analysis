interface HeaderProps {
  title: string
  sub?: string
}

export function Header({ title, sub }: HeaderProps) {
  return (
    <header className="header">
      <span className="header-title">{title}</span>
      {sub && <span className="header-sub">{sub}</span>}
    </header>
  )
}
