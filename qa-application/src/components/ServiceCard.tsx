import { Link } from 'react-router-dom';

interface ServiceCardProps {
  title: string;
  description: string;
  icon: string;
  link?: string;
  status?: 'available' | 'planned';
}

export default function ServiceCard({
  title,
  description,
  icon,
  link,
  status = 'planned',
}: ServiceCardProps) {
  const content = (
    <div
      className={`h-full rounded-2xl border p-6 shadow-sm transition ${
        status === 'available'
          ? 'border-red-200 bg-white hover:-translate-y-0.5 hover:border-red-600 hover:shadow-md'
          : 'border-stone-200 bg-stone-100 text-stone-600'
      }`}
    >
      <div className="flex items-start justify-between gap-4">
        <span aria-hidden="true" className="text-3xl">
          {icon}
        </span>
        <span className="rounded-full bg-stone-200 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-stone-700">
          {status === 'available' ? 'Disponível' : 'Planejado'}
        </span>
      </div>
      <h2 className="mt-6 text-xl font-bold text-stone-950">{title}</h2>
      <p className="mt-2 leading-relaxed">{description}</p>
    </div>
  );

  if (status === 'available' && link) {
    return (
      <Link className="block rounded-2xl focus:outline-none focus:ring-2 focus:ring-red-700" to={link}>
        {content}
      </Link>
    );
  }

  return <article aria-disabled="true">{content}</article>;
}
