import React from 'react';
import { Route, Routes } from 'react-router-dom';
import Home from './pages/Home';
import Rank from './pages/Evaluation';

const App: React.FC = () => {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/evaluation" element={<Rank />} />
    </Routes>
  );
}

export default App;
