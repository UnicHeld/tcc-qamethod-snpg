import { NavLink } from 'react-router-dom';

const linkClassName = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-3 py-2 text-sm font-medium transition focus:outline-none focus:ring-2 focus:ring-white ${
    isActive ? 'bg-white text-stone-950' : 'text-stone-200 hover:bg-stone-800 hover:text-white'
  }`;

export default function Navbar() {
  return (
    <nav aria-label="Navegação principal" className="bg-stone-950 text-white">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
        <NavLink className="font-bold tracking-tight" to="/">
          QA Method <span className="font-normal text-red-400">· Laboratório</span>
        </NavLink>
        <div className="flex gap-1">
          <NavLink className={linkClassName} end to="/">
            Início
          </NavLink>
          <NavLink className={linkClassName} to="/evaluation">
            Avaliação
          </NavLink>
        </div>
      </div>
    </nav>
  );
}
