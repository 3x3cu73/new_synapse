// import React from 'react';
// import { NavLink } from 'react-router-dom';
// import { LayoutDashboard, User, Calendar, LogOut, Shield, Layout } from 'lucide-react';
// import { useAuth } from '../../context/AuthContext';

// const Sidebar = () => {
//   const { user, logout } = useAuth();
//   const hasManagementAccess = user?.is_superuser || (user?.authorizations && user.authorizations.length > 0);

//   return (
//     <div className="sidebar d-flex flex-column justify-content-between p-3">
//       <div>
//         {/* Professional Brand Section: Stacked & Centered */}
//         <div className="sidebar-brand-minimal d-flex flex-column align-items-center mb-5 px-3 pt-2">
//           <NavLink to="/" className="text-decoration-none d-flex flex-column align-items-center">
//             <img
//               src="/assets/logo_nobgn.png" 
//               alt="Synapse"
//               className="sidebar-logo-standalone mb-3"
//             />
//             <span className="sidebar-brand-text">SYNAPSE</span>
//           </NavLink>
//         </div>

//         <ul className="nav flex-column gap-2">
//           {/* ... Navigation items remain the same ... */}
//           <li className="nav-item">
//             <NavLink to="/" className={({ isActive }) => `nav-link d-flex align-items-center gap-3 ${isActive ? 'active-link' : 'text-secondary'}`}>
//               <LayoutDashboard size={20} /> Events Feed
//             </NavLink>
//           </li>
          
//           {user && (
//             <li className="nav-item">
//               <NavLink to="/dashboard" className={({ isActive }) => `nav-link d-flex align-items-center gap-3 ${isActive ? 'active-link' : 'text-secondary'}`}>
//                 <Calendar size={20} /> My Calendar
//               </NavLink>
//             </li>
//           )}
          
//           {user && (
//             <li className="nav-item">
//               <NavLink to="/profile" className={({ isActive }) => `nav-link d-flex align-items-center gap-3 ${isActive ? 'active-link' : 'text-secondary'}`}>
//                 <User size={20} /> My Profile
//               </NavLink>
//             </li>
//           )}

//           {hasManagementAccess && (
//             <div className="mt-4 pt-4 border-top" style={{ borderColor: 'var(--border-primary) !important' }}>
//               <small className="text-muted text-uppercase fw-bold px-3 mb-2 d-block" style={{ fontSize: '0.65rem', letterSpacing: '1px', opacity: 0.5 }}>
//                 Management
//               </small>
//               {user?.is_superuser && (
//                 <NavLink to="/admin" className="nav-link d-flex align-items-center gap-3 text-danger-emphasis">
//                   <Shield size={20} /> Admin Panel
//                 </NavLink>
//               )}
//               {user?.authorizations?.map((auth, idx) => (
//                 <NavLink key={idx} to={`/org/${auth.id}/dashboard`} className="nav-link d-flex align-items-center gap-3 text-warning-emphasis">
//                   <Layout size={20} /> {auth.org_name}
//                 </NavLink>
//               ))}
//             </div>
//           )}
//         </ul>
//       </div>

//       {user && (
//         <button onClick={logout} className="logout-btn-minimal d-flex align-items-center gap-2 justify-content-center w-100 mb-2">
//           <LogOut size={18} /> Logout
//         </button>
//       )}
//     </div>
//   );
// };

// export default Sidebar;

import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, User, Calendar, LogOut, Shield, Layout, X, PanelLeftClose, PanelLeft, Home } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { capitalize, orgDisplayName } from '../../utils/capitalize';
import OrgLogo from '../UI/OrgLogo';

const MobileNav = ({ user, hasManagementAccess, logout }) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const closeMobileMenu = () => setMobileMenuOpen(false);

  return (
    <>
      <nav className="mobile-bottom-nav">
        <NavLink to="/" end className={({ isActive }) => `mobile-nav-item ${isActive ? 'active' : ''}`}>
          <Home size={22} /><span>Home</span>
        </NavLink>
        <NavLink to="/events" className={({ isActive }) => `mobile-nav-item ${isActive ? 'active' : ''}`}>
          <LayoutDashboard size={22} /><span>Events</span>
        </NavLink>
        {user && (
          <NavLink to="/dashboard" className={({ isActive }) => `mobile-nav-item ${isActive ? 'active' : ''}`}>
            <Calendar size={22} /><span>Calendar</span>
          </NavLink>
        )}
        {user && (
          <NavLink to="/profile" className={({ isActive }) => `mobile-nav-item ${isActive ? 'active' : ''}`}>
            <User size={22} /><span>Profile</span>
          </NavLink>
        )}
        {hasManagementAccess && (
          <button className="mobile-nav-item" onClick={() => setMobileMenuOpen(true)}>
            <Layout size={22} /><span>Manage</span>
          </button>
        )}
      </nav>

      {mobileMenuOpen && (
        <>
          <div className="mobile-drawer-backdrop" onClick={closeMobileMenu} />
          <div className="mobile-drawer">
            <div className="mobile-drawer-handle" />
            <div className="d-flex justify-content-between align-items-center mb-4">
              <h6 className="fw-bold m-0" style={{ color: 'var(--text-primary)' }}>Management</h6>
              <button onClick={closeMobileMenu} style={{ background: 'var(--bg-input)', border: 'none', borderRadius: '8px', padding: '6px 8px', color: 'var(--text-secondary)', cursor: 'pointer' }}>
                <X size={18} />
              </button>
            </div>
            <div className="d-flex flex-column gap-2">
              {user?.is_superuser && (
                <NavLink to="/admin" className="mobile-drawer-link" onClick={closeMobileMenu}>
                  <Shield size={18} /> Admin Panel
                </NavLink>
              )}
              {user?.roles?.map((role, idx) => {
                const label = role.organization?.name || orgDisplayName(role.organization?.name);
                return (
                <NavLink key={idx} to={`/org/${role.org_id}/dashboard`} className="mobile-drawer-link" onClick={closeMobileMenu}>
                  {role.organization?.banner_url ? (
                    <img src={role.organization.banner_url} alt="" className="sidebar-org-img" />
                  ) : (
                    <OrgLogo orgName={label} size={18} />
                  )} {label}
                </NavLink>
                );
              })}
              {user && (
                <button onClick={() => { logout(); closeMobileMenu(); }} className="mobile-drawer-logout">
                  <LogOut size={18} /> Logout
                </button>
              )}
            </div>
          </div>
        </>
      )}
    </>
  );
};

const Sidebar = ({ mobileOnly = false, collapsed, onToggle }) => {
  const { user, logout } = useAuth();
  const hasManagementAccess = user?.is_superuser === true || (Array.isArray(user?.roles) && user.roles.length > 0);

  if (mobileOnly) {
    return <MobileNav user={user} hasManagementAccess={hasManagementAccess} logout={logout} />;
  }

  return (
    <div className={`sidebar-v2 ${collapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-v2-inner">
        {/* Header */}
        <div className="sidebar-v2-header">
          {!collapsed && (
            <NavLink to="/" className="sidebar-v2-brand">
              <img src="/assets/logo_nobgn.png" alt="Synapse" className="sidebar-v2-logo" />
              <span className="sidebar-v2-brand-text">SYNAPSE</span>
            </NavLink>
          )}
          <button className="sidebar-v2-toggle" onClick={onToggle} title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}>
            {collapsed ? <PanelLeft size={18} /> : <PanelLeftClose size={18} />}
          </button>
        </div>

        {/* Navigation */}
        <nav className="sidebar-v2-nav">
          <NavLink to="/" end className={({ isActive }) => `sidebar-v2-link ${isActive ? 'active' : ''}`}>
            <Home size={19} />
            {!collapsed && <span>Home</span>}
          </NavLink>

          <NavLink to="/events" className={({ isActive }) => `sidebar-v2-link ${isActive ? 'active' : ''}`}>
            <LayoutDashboard size={19} />
            {!collapsed && <span>Events Feed</span>}
          </NavLink>

          {user && (
            <NavLink to="/dashboard" className={({ isActive }) => `sidebar-v2-link ${isActive ? 'active' : ''}`}>
              <Calendar size={19} />
              {!collapsed && <span>My Calendar</span>}
            </NavLink>
          )}

          {user && (
            <NavLink to="/profile" className={({ isActive }) => `sidebar-v2-link ${isActive ? 'active' : ''}`}>
              <User size={19} />
              {!collapsed && <span>My Profile</span>}
            </NavLink>
          )}

          {hasManagementAccess && (
            <>
              <div className="sidebar-v2-divider" />
              {!collapsed && <div className="sidebar-v2-section-label">Management</div>}
              {user?.is_superuser && (
                <NavLink to="/admin" className={({ isActive }) => `sidebar-v2-link ${isActive ? 'active' : ''}`}>
                  <Shield size={19} />
                  {!collapsed && <span>Admin Panel</span>}
                </NavLink>
              )}
              {user?.roles?.map((role, idx) => {
                const label = role.organization?.name || orgDisplayName(role.organization?.name);
                return (
                <NavLink key={idx} to={`/org/${role.org_id}/dashboard`}
                  className={({ isActive }) => `sidebar-v2-link ${isActive ? 'active' : ''}`}>
                  {role.organization?.banner_url ? (
                    <img src={role.organization.banner_url} alt="" className="sidebar-org-img" />
                  ) : (
                    <OrgLogo orgName={label} size={20} />
                  )}
                  {!collapsed && <span>{label}</span>}
                </NavLink>
                );
              })}
            </>
          )}
        </nav>

        {/* Footer */}
        {user && (
          <div className="sidebar-v2-footer">
            <button onClick={logout} className="sidebar-v2-link logout">
              <LogOut size={19} />
              {!collapsed && <span>Logout</span>}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default Sidebar;