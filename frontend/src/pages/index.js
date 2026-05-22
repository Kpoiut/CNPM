/**
 * Pages barrel export — centralized lazy imports.
 * Grouped by access level: public (user) vs admin.
 */
import { lazy } from 'react'

// --- Public pages (role: user / public) ---
export const Prediction      = lazy(() => import('./public/Prediction'))
export const BuyerSurvey     = lazy(() => import('./public/BuyerSurvey'))
export const Dashboard       = lazy(() => import('./public/Dashboard'))
export const DataExplorer    = lazy(() => import('./public/DataExplorer'))
export const MapExplorer     = lazy(() => import('./public/MapExplorer'))
export const DataQuality     = lazy(() => import('./public/DataQuality'))
export const RecordExplorer  = lazy(() => import('./public/RecordExplorer'))
export const Community       = lazy(() => import('./public/Community'))
export const About           = lazy(() => import('./public/About'))
export const Login           = lazy(() => import('./public/Login'))

// --- Admin pages (role: admin) ---
export const DataCollector        = lazy(() => import('./admin/DataCollector'))
export const CollectionDashboard  = lazy(() => import('./admin/CollectionDashboard'))
export const ProvenanceTracker    = lazy(() => import('./admin/ProvenanceTracker'))
export const ResearchLab          = lazy(() => import('./admin/ResearchLab'))
export const SelfCollected        = lazy(() => import('./admin/SelfCollected'))
export const DataSources          = lazy(() => import('./admin/DataSources'))
export const CommunityAdmin       = lazy(() => import('./admin/CommunityAdmin'))
export const UserManagement       = lazy(() => import('./admin/UserManagement'))
