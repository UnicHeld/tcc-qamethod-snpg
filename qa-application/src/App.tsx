import { Route, Routes } from 'react-router-dom';

import Evaluation from './pages/Evaluation';
import Home from './pages/Home';
import Insights from './pages/Insights';
import Search from './pages/Search';

export default function App() {
  return (
    <Routes>
      <Route element={<Home />} path="/" />
      <Route element={<Evaluation />} path="/evaluation" />
      <Route element={<Search />} path="/search" />
      <Route element={<Insights />} path="/insights" />
    </Routes>
  );
}
