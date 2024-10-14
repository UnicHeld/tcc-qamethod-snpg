// src/components/Navbar.tsx
import React from 'react';
import { Link } from 'react-router-dom';

const Navbar: React.FC = () => {
    return (
        <nav className="bg-black text-white py-4">
            <div className="container mx-auto flex justify-between items-center">
                {/* Logo */}
                <div className="text-2xl font-bold text-red-600">
                    D&T Retrieval
                </div>

                {/* Menu */}
                <ul className="flex space-x-6">
                    <li>
                        <Link to="/" className="hover:text-red-500">
                            Home
                        </Link>
                    </li>
                    <li>
                        <Link to="/sobre" className="hover:text-red-500">
                            Sobre
                        </Link>
                    </li>
                    <li>
                        <Link to="/contato" className="hover:text-red-500">
                            Contato
                        </Link>
                    </li>
                </ul>
            </div>
        </nav>
    );
}

export default Navbar;
