// src/components/Footer.tsx
import React from 'react';

const Footer: React.FC = () => {
    return (
        <footer className="bg-black text-white text-center py-4">
            <p>
                &copy; 2024. D&T Retrieval - Desenvolvido por
                <a
                    href="https://www.linkedin.com/in/theHprogrammer/"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-bold hover:underline hover:text-red-500 ml-1"
                >
                    Helder Henrique
                </a>
            </p>
        </footer>
    );
}

export default Footer;
