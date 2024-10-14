// src/components/ServiceCard.tsx
import React from 'react';
import { Link } from 'react-router-dom';

interface ServiceCardProps {
    title: string;
    description: string;
    icon: string;
    link?: string;  // Adiciona a opção de link
}

const ServiceCard: React.FC<ServiceCardProps> = ({ title, description, icon, link }) => {
    return (
        <Link to={link || "#"} className="block">
            <div className="bg-red-600 text-white p-6 rounded-lg shadow-lg hover:bg-red-700 transition duration-300">
                <div className="text-4xl mb-4">{icon}</div>
                <h3 className="text-xl font-bold mb-2">{title}</h3>
                <p>{description}</p>
            </div>
        </Link>
    );
}

export default ServiceCard;
