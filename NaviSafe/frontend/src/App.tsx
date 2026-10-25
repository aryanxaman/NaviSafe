import { Suspense, lazy, useEffect, useState } from 'react';
import { HashRouter, Navigate, Route, Routes, useParams } from 'react-router-dom';
import Navigation from './components/Navigation';
import { SystemTools, EmergencyButton } from './components/SystemTools';
import HomePage from './pages/HomePage';
import LandingPage from './pages/LandingPage';
import AuthPage from './pages/AuthPage';
import OnboardingPage from './pages/OnboardingPage';
import ReportPage from './pages/ReportPage';
import CheckInPage from './pages/CheckInPage';
import ProfilePage from './pages/ProfilePage';
import { readLocal } from './services';
import './App.css';
import './upgrade.css';
const MapPage=lazy(()=>import('./pages/MapPage'));
const AnalyticsPage=lazy(()=>import('./pages/AnalyticsPage'));
const ModerationPage=lazy(()=>import('./pages/ModerationPage'));
export default function App(){
 const [hour,setHour]=useState(20),[alpha,setAlpha]=useState(2),[isOffline,setOffline]=useState(!navigator.onLine);
 useEffect(()=>{const update=()=>setOffline(!navigator.onLine);window.addEventListener('online',update);window.addEventListener('offline',update);return()=>{window.removeEventListener('online',update);window.removeEventListener('offline',update);};},[]);
 return <HashRouter><a className="skip-link" href="#main-content" onClick={e=>{e.preventDefault();document.getElementById("main-content")?.focus();}}>Skip to content</a><div className="app-shell"><Navigation/><main className="app-main" id="main-content" tabIndex={-1}><SystemTools/><Suspense fallback={<div className="page" role="status">Loading your workspace…</div>}><Routes><Route path="/" element={readLocal('safepath-onboarded',false)?<Navigate to="/home" replace/>:<LandingPage/>}/><Route path="/welcome" element={<LandingPage/>}/><Route path="/create-account" element={<AuthPage mode="create"/>}/><Route path="/signin" element={<AuthPage mode="signin"/>}/><Route path="/onboarding/:step" element={<OnboardingRoute/>}/><Route path="/home" element={<HomePage isOffline={isOffline}/>}/><Route path="/navigate/*" element={<MapPage hour={hour} setHour={setHour} alpha={alpha} setAlpha={setAlpha}/>}/><Route path="/analysis" element={<AnalyticsPage hour={hour} setHour={setHour}/>}/><Route path="/analytics" element={<Navigate to="/analysis" replace/>}/><Route path="/community/*" element={<ReportPage/>}/><Route path="/report" element={<Navigate to="/community/create" replace/>}/><Route path="/check-in/*" element={<CheckInPage/>}/><Route path="/profile/*" element={<ProfilePage/>}/><Route path="/moderation" element={<ModerationPage/>}/><Route path="*" element={<Navigate to="/home" replace/>}/></Routes></Suspense><EmergencyButton/></main></div></HashRouter>;
}
function OnboardingRoute(){const {step='intro'}=useParams();return <OnboardingPage key={step} step={step}/>;}
