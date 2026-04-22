interface CardProps {
  children: React.ReactNode;
  className?: string;
}

export default function Card({ children, className = "" }: CardProps) {
  return (
    <div
      className={`bg-white rounded-2xl p-6 shadow-sm border border-slate-200 ${className}`}
    >
      {children}
    </div>
  );
}
