import { Route, Routes } from 'react-router-dom';

import Evaluation from './pages/Evaluation';
import Home from './pages/Home';

export default function App() {
  return (
    <Routes>
      <Route element={<Home />} path="/" />
      <Route element={<Evaluation />} path="/evaluation" />
    </Routes>
  );
}
