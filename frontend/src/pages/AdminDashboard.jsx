import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { createPortal } from 'react-dom';
import api from '../api/axios';
import {
  Search, ShieldAlert, Trash2, UserCheck, PlusCircle, X, Users,
  Building2, BarChart3, Edit2, Plus, ChevronDown, ChevronRight,
  AlertTriangle, TrendingUp, Calendar, UserX, Shield, Key, Copy, Eye, EyeOff
} from 'lucide-react';
import Loader from '../components/UI/Loader';
import ConfirmationModal from '../components/UI/ConfirmationModal';
import OrgLogo from '../components/UI/OrgLogo';
import toast from 'react-hot-toast';
import { capitalize, orgDisplayName } from '../utils/capitalize';

import { ALL_ROLES, ORG_TYPES } from '../utils/constants';
import SearchableDropdown from '../components/UI/SearchableDropdown';

const UserAvatar = ({ name, photoUrl, size = 38 }) => {
  const style = {
    width: size, height: size, borderRadius: '10px',
    background: 'var(--brand-gradient)', color: 'white',
    fontWeight: 700, fontSize: size * 0.36 + 'px',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    flexShrink: 0, overflow: 'hidden',
  };
  if (photoUrl) {
    return (
      <div style={style}>
        <img src={photoUrl} alt={name}
          style={{ width: '100%', height: '100%', objectFit: 'cover' }}
          onError={e => { e.currentTarget.style.display = 'none'; e.currentTarget.parentElement.textContent = name?.charAt(0) || '?'; }}
        />
      </div>
    );
  }
  return <div style={style}>{name?.charAt(0) || '?'}</div>;
};

const TABS = [
  { key: 'users', label: 'Users', icon: Users },
  { key: 'orgs', label: 'Organizations', icon: Building2 },
  { key: 'analytics', label: 'Analytics', icon: BarChart3 },
];

// ─── USERS TAB ────────────────────────────────────────────
const UsersTab = ({ users, totalUsers, orgs, onRefresh, onLoadMore, loadingMore, hasMore, onFetchOrgs }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedUser, setSelectedUser] = useState(null);
  const [authForm, setAuthForm] = useState({ org_id: '', role_name: 'overall coordinator' });
  const [revokeModalOpen, setRevokeModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [roleToRevoke, setRoleToRevoke] = useState(null);
  const [userToDelete, setUserToDelete] = useState(null);
  const sentinelRef = useRef(null);

  useEffect(() => {
    if (orgs.length > 0 && !authForm.org_id) {
      setAuthForm(prev => ({ ...prev, org_id: orgs[0].id }));
    }
  }, [orgs, authForm.org_id]);

  // Fetch orgs when user selects someone for role assignment
  useEffect(() => {
    if (selectedUser && orgs.length === 0) onFetchOrgs();
  }, [selectedUser, orgs.length, onFetchOrgs]);

  // Infinite scroll observer
  useEffect(() => {
    if (!sentinelRef.current || !hasMore || loadingMore) return;
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) onLoadMore(); },
      { rootMargin: '200px' }
    );
    observer.observe(sentinelRef.current);
    return () => observer.disconnect();
  }, [hasMore, loadingMore, onLoadMore]);

  const filteredUsers = useMemo(() => {
    const q = searchTerm.toLowerCase();
    return users.filter(u =>
      u.name.toLowerCase().includes(q) ||
      u.email.toLowerCase().includes(q) ||
      (u.entry_number || '').toLowerCase().includes(q)
    );
  }, [searchTerm, users]);

  const handleAuthorize = async (e) => {
    e.preventDefault();
    if (!selectedUser || !authForm.org_id) return;
    try {
      await api.post(`/admin/authorize?email=${encodeURIComponent(selectedUser.email)}`, {
        org_id: parseInt(authForm.org_id), role_name: authForm.role_name
      });
      toast.success(`Role assigned to ${selectedUser.name}`);
      setSelectedUser(null);
      onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to authorize");
    }
  };

  const handleRevoke = async () => {
    if (!roleToRevoke) return;
    try {
      await api.delete(`/admin/revoke?email=${encodeURIComponent(roleToRevoke.email)}&org_id=${roleToRevoke.org_id}`);
      toast.success("Role revoked");
      onRefresh();
    } catch { toast.error("Failed to revoke"); }
    setRevokeModalOpen(false);
    setRoleToRevoke(null);
  };

  const handleDeleteUser = async () => {
    if (!userToDelete) return;
    try {
      await api.delete(`/admin/users/${userToDelete.id}`);
      toast.success(`Deleted ${userToDelete.name}`);
      onRefresh();
    } catch (err) { toast.error(err.response?.data?.detail || "Failed to delete user"); }
    setDeleteModalOpen(false);
    setUserToDelete(null);
  };

  const usersWithRoles = users.filter(u => u.roles?.length > 0).length;

  return (
    <>
      {/* Stats row */}
      <div className="row g-3 mb-4">
        <div className="col-6 col-lg-3">
          <div className="admin-stat-card">
            <div className="admin-stat-icon" style={{ background: 'var(--brand-primary-soft)', color: 'var(--brand-primary)' }}>
              <Users size={20} />
            </div>
            <div>
              <div className="admin-stat-value">{totalUsers}</div>
              <div className="admin-stat-label">Total Users</div>
            </div>
          </div>
        </div>
        <div className="col-6 col-lg-3">
          <div className="admin-stat-card">
            <div className="admin-stat-icon" style={{ background: 'var(--success-soft)', color: 'var(--success)' }}>
              <Shield size={20} />
            </div>
            <div>
              <div className="admin-stat-value">{usersWithRoles}</div>
              <div className="admin-stat-label">With Roles</div>
            </div>
          </div>
        </div>
        <div className="col-6 col-lg-3">
          <div className="admin-stat-card">
            <div className="admin-stat-icon" style={{ background: 'var(--info-soft)', color: 'var(--info)' }}>
              <Building2 size={20} />
            </div>
            <div>
              <div className="admin-stat-value">{orgs.length}</div>
              <div className="admin-stat-label">Organizations</div>
            </div>
          </div>
        </div>
        <div className="col-6 col-lg-3">
          <div className="admin-stat-card">
            <div className="admin-stat-icon" style={{ background: 'var(--warning-soft)', color: 'var(--warning)' }}>
              <UserX size={20} />
            </div>
            <div>
              <div className="admin-stat-value">{users.length - usersWithRoles}</div>
              <div className="admin-stat-label">Students Only</div>
            </div>
          </div>
        </div>
      </div>

      <div className="row g-4">
        {/* User list */}
        <div className="col-12 col-lg-8">
          <div className="admin-panel">
            <div className="admin-panel-header">
              <h6 className="admin-panel-title"><Users size={16} /> All Users</h6>
              <div className="admin-search-bar">
                <Search size={15} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
                <input type="text" placeholder="Search by name, email, or entry number..."
                  value={searchTerm} onChange={e => setSearchTerm(e.target.value)} />
                {searchTerm && (
                  <button className="btn p-0 border-0 bg-transparent d-flex" onClick={() => setSearchTerm('')}>
                    <X size={14} style={{ color: 'var(--text-muted)' }} />
                  </button>
                )}
              </div>
            </div>
            <div className="admin-panel-body">
              <div className="admin-table-scroll">
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>User</th>
                      <th className="d-none d-md-table-cell">Email</th>
                      <th className="d-none d-lg-table-cell">Roles</th>
                      <th style={{ width: 80 }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredUsers.length === 0 ? (
                      <tr><td colSpan={4} className="text-center py-5" style={{ color: 'var(--text-muted)' }}>No users found</td></tr>
                    ) : filteredUsers.map(user => (
                      <tr key={user.id} className={selectedUser?.id === user.id ? 'row-active' : ''}>
                        <td>
                          <div className="d-flex align-items-center gap-2">
                            <UserAvatar name={user.name} photoUrl={user.photo_url} size={34} />
                            <div style={{ minWidth: 0 }}>
                              <div className="admin-cell-name">{user.name}</div>
                              <div className="admin-cell-meta">
                                {user.entry_number || 'No entry number'}
                              </div>
                              <div className="d-md-none admin-cell-meta" style={{ fontSize: '0.7rem' }}>{user.email}</div>
                            </div>
                          </div>
                        </td>
                        <td className="d-none d-md-table-cell">
                          <span className="admin-cell-mono">{user.email}</span>
                        </td>
                        <td className="d-none d-lg-table-cell">
                          <div className="d-flex flex-wrap gap-1">
                            {user.roles?.length > 0 ? user.roles.map(role => (
                              <span key={role.id} className="admin-role-chip">
                                <span className="admin-role-org">{orgDisplayName(role.organization?.name)}</span>
                                <span className="admin-role-name">{role.role_name}</span>
                                <button className="admin-role-revoke" onClick={e => {
                                  e.stopPropagation();
                                  setRoleToRevoke({ email: user.email, org_id: role.org_id });
                                  setRevokeModalOpen(true);
                                }}><X size={10} /></button>
                              </span>
                            )) : <span className="admin-cell-meta">No roles</span>}
                          </div>
                        </td>
                        <td>
                          <div className="d-flex gap-1 flex-wrap">
                            <button className="admin-btn-sm primary" onClick={() => setSelectedUser(user)} title="Assign role">
                              <UserCheck size={14} />
                            </button>
                            <button className="admin-btn-sm danger" title="Delete user"
                              onClick={() => { setUserToDelete(user); setDeleteModalOpen(true); }}>
                              <Trash2 size={14} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {filteredUsers.length > 0 && (
                <div className="admin-table-footer">
                  Showing {users.length} of {totalUsers} users
                  {searchTerm && ` (${filteredUsers.length} matching)`}
                </div>
              )}
              {/* Infinite scroll sentinel */}
              <div ref={sentinelRef} style={{ height: 1 }} />
              {loadingMore && (
                <div className="d-flex justify-content-center py-3">
                  <Loader />
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Assign role panel — desktop sidebar */}
        <div className="col-12 col-lg-4 d-none d-lg-block">
          <div className="admin-panel">
            <div className="admin-panel-header">
              <h6 className="admin-panel-title"><ShieldAlert size={16} /> Assign Role</h6>
            </div>
            <div className="admin-panel-body">
              {!selectedUser ? (
                <div className="admin-empty-state">
                  <UserCheck size={36} strokeWidth={1.5} />
                  <p>Select a user from the table to assign a role</p>
                </div>
              ) : (
                <form onSubmit={handleAuthorize}>
                  <div className="selected-user-card mb-3">
                    <UserAvatar name={selectedUser.name} photoUrl={selectedUser.photo_url} size={38} />
                    <div className="selected-user-info">
                      <div className="selected-user-name">{selectedUser.name}</div>
                      <div className="selected-user-email">{selectedUser.email}</div>
                    </div>
                    <button type="button" className="btn p-0 border-0 bg-transparent d-flex"
                      onClick={() => setSelectedUser(null)}>
                      <X size={14} style={{ color: 'var(--text-muted)' }} />
                    </button>
                  </div>

                  {selectedUser.roles?.length > 0 && (
                    <div className="mb-3">
                      <label className="admin-form-label">Current Roles</label>
                      <div className="d-flex flex-wrap gap-1">
                        {selectedUser.roles.map(r => (
                          <span key={r.id} className="admin-role-chip">
                            <span className="admin-role-org">{orgDisplayName(r.organization?.name)}</span>
                            <span className="admin-role-name">{r.role_name}</span>
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="mb-3">
                    <label className="admin-form-label">Organization</label>
                    <SearchableDropdown
                      className="sd-admin"
                      options={orgs.map(org => ({ label: `${orgDisplayName(org.name)} (${org.org_type})`, value: org.id }))}
                      value={authForm.org_id}
                      onChange={(val) => setAuthForm({ ...authForm, org_id: val })}
                      placeholder="Select organization..."
                    />
                  </div>

                  <div className="mb-4">
                    <label className="admin-form-label">Role</label>
                    <SearchableDropdown
                      className="sd-admin"
                      options={ALL_ROLES}
                      value={authForm.role_name}
                      onChange={(val) => setAuthForm({ ...authForm, role_name: val })}
                      placeholder="Select role..."
                    />
                  </div>

                  <button type="submit" className="admin-btn-primary w-100">
                    <PlusCircle size={16} /> Assign Role
                  </button>
                </form>
              )}
            </div>
          </div>
        </div>

        {/* Assign role modal — mobile only */}
        {selectedUser && createPortal(
          <div className="admin-modal-overlay d-lg-none" onClick={() => setSelectedUser(null)}>
            <div className="admin-modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 440 }}>
              <div className="admin-modal-header">
                <h6 className="fw-bold m-0" style={{ color: 'var(--text-primary)' }}>
                  <ShieldAlert size={16} style={{ marginRight: 6 }} /> Assign Role
                </h6>
                <button className="btn p-0 border-0 bg-transparent d-flex" onClick={() => setSelectedUser(null)}>
                  <X size={18} style={{ color: 'var(--text-muted)' }} />
                </button>
              </div>
              <div className="admin-modal-body">
                <form onSubmit={handleAuthorize}>
                  <div className="selected-user-card mb-3">
                    <UserAvatar name={selectedUser.name} photoUrl={selectedUser.photo_url} size={38} />
                    <div className="selected-user-info">
                      <div className="selected-user-name">{selectedUser.name}</div>
                      <div className="selected-user-email">{selectedUser.email}</div>
                    </div>
                  </div>

                  {selectedUser.roles?.length > 0 && (
                    <div className="mb-3">
                      <label className="admin-form-label">Current Roles</label>
                      <div className="d-flex flex-wrap gap-1">
                        {selectedUser.roles.map(r => (
                          <span key={r.id} className="admin-role-chip">
                            <span className="admin-role-org">{orgDisplayName(r.organization?.name)}</span>
                            <span className="admin-role-name">{r.role_name}</span>
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="mb-3">
                    <label className="admin-form-label">Organization</label>
                    <SearchableDropdown
                      className="sd-admin"
                      options={orgs.map(org => ({ label: `${orgDisplayName(org.name)} (${org.org_type})`, value: org.id }))}
                      value={authForm.org_id}
                      onChange={(val) => setAuthForm({ ...authForm, org_id: val })}
                      placeholder="Select organization..."
                    />
                  </div>

                  <div className="mb-4">
                    <label className="admin-form-label">Role</label>
                    <SearchableDropdown
                      className="sd-admin"
                      options={ALL_ROLES}
                      value={authForm.role_name}
                      onChange={(val) => setAuthForm({ ...authForm, role_name: val })}
                      placeholder="Select role..."
                    />
                  </div>

                  <button type="submit" className="admin-btn-primary w-100">
                    <PlusCircle size={16} /> Assign Role
                  </button>
                </form>
              </div>
            </div>
          </div>,
          document.body
        )}
      </div>

      <ConfirmationModal isOpen={revokeModalOpen} onClose={() => setRevokeModalOpen(false)}
        onConfirm={handleRevoke} title="Revoke Role"
        message="This will remove the role immediately. The user will lose access to this organization." />
      <ConfirmationModal isOpen={deleteModalOpen} onClose={() => setDeleteModalOpen(false)}
        onConfirm={handleDeleteUser} title="Delete User"
        message={`Are you sure you want to delete ${userToDelete?.name}? This action cannot be undone.`} />
    </>
  );
};

// ─── API KEY MODAL ────────────────────────────────────────
const ApiKeyModal = ({ org, onClose }) => {
  const [generating, setGenerating] = useState(false);
  const [newKey, setNewKey] = useState(null);
  const [copied, setCopied] = useState('');

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const res = await api.post(`/admin/orgs/${org.id}/api-keys`);
      setNewKey(res.data);
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed to generate key'); }
    setGenerating(false);
  };

  const copyToClipboard = (text, field) => {
    navigator.clipboard.writeText(text);
    setCopied(field);
    setTimeout(() => setCopied(''), 2000);
  };

  return (
    <div className="admin-modal-overlay" onClick={onClose}>
      <div className="admin-modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 500 }}>
        <div className="admin-modal-header">
          <h6 className="admin-panel-title"><Key size={16} /> API Key — {org.name}</h6>
          <button className="btn p-0 border-0 bg-transparent d-flex" onClick={onClose}><X size={16} style={{ color: 'var(--text-secondary)' }} /></button>
        </div>
        <div className="admin-modal-body">

          {newKey ? (
            <div className="admin-key-reveal">
              <div className="d-flex align-items-center gap-2 mb-3">
                <AlertTriangle size={16} style={{ color: 'var(--warning)' }} />
                <strong style={{ color: 'var(--warning)', fontSize: '0.85rem' }}>Copy now — this key will not be shown again!</strong>
              </div>
              <div className="admin-key-field mb-3">
                <span className="admin-key-label">Organization ID</span>
                <div className="admin-key-copy-row">
                  <code className="admin-key-code">{org.id}</code>
                  <button className="admin-btn-sm primary" onClick={() => copyToClipboard(String(org.id), 'orgId')}>
                    {copied === 'orgId' ? '✓' : <Copy size={13} />}
                  </button>
                </div>
              </div>
              <div className="admin-key-field">
                <span className="admin-key-label">API Key</span>
                <div className="admin-key-copy-row">
                  <code className="admin-key-code">{newKey.key}</code>
                  <button className="admin-btn-sm primary" onClick={() => copyToClipboard(newKey.key, 'apiKey')}>
                    {copied === 'apiKey' ? '✓' : <Copy size={13} />}
                  </button>
                </div>
              </div>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: 14, marginBottom: 0 }}>
                Any previously active key for this organization has been revoked.
              </p>
            </div>
          ) : (
            <div className="text-center" style={{ padding: '24px 0' }}>
              <Key size={36} strokeWidth={1.5} style={{ color: 'var(--text-muted)', marginBottom: 12 }} />
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', marginBottom: 20 }}>
                Generate a new API key for external integrations.<br/>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>This will revoke any existing key.</span>
              </p>
              <button className="admin-btn-primary" onClick={handleGenerate} disabled={generating}
                style={{ minWidth: 180 }}>
                {generating ? 'Generating...' : <><Key size={14} /> Generate New Key</>}
              </button>
            </div>
          )}

        </div>
      </div>
    </div>
  );
};

// ─── ORGANIZATIONS TAB ────────────────────────────────────
const OrgsTab = ({ orgs, onRefresh }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editingOrg, setEditingOrg] = useState(null);
  const [form, setForm] = useState({ name: '', org_type: 'club' });
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [orgToDelete, setOrgToDelete] = useState(null);
  const [apiKeyOrg, setApiKeyOrg] = useState(null);

  const filtered = useMemo(() => {
    return orgs.filter(o => {
      const matchName = o.name.toLowerCase().includes(searchTerm.toLowerCase());
      const matchType = !filterType || o.org_type === filterType;
      return matchName && matchType;
    });
  }, [orgs, searchTerm, filterType]);

  const typeCounts = useMemo(() => {
    const c = {};
    orgs.forEach(o => { c[o.org_type] = (c[o.org_type] || 0) + 1; });
    return c;
  }, [orgs]);

  const openCreate = () => {
    setEditingOrg(null);
    setForm({ name: '', org_type: 'club' });
    setShowForm(true);
  };

  const openEdit = (org) => {
    setEditingOrg(org);
    setForm({ name: org.name, org_type: org.org_type });
    setShowForm(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) return;
    try {
      if (editingOrg) {
        await api.put(`/admin/orgs/${editingOrg.id}`, form);
        toast.success(`Updated ${form.name}`);
      } else {
        await api.post('/admin/orgs', form);
        toast.success(`Created ${form.name}`);
      }
      setShowForm(false);
      setEditingOrg(null);
      onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Operation failed");
    }
  };

  const handleDelete = async () => {
    if (!orgToDelete) return;
    try {
      await api.delete(`/admin/orgs/${orgToDelete.id}`);
      toast.success(`Deleted ${orgToDelete.name}`);
      onRefresh();
    } catch (err) { toast.error(err.response?.data?.detail || "Failed to delete"); }
    setDeleteModalOpen(false);
    setOrgToDelete(null);
  };

  return (
    <>
      {/* Type filter chips */}
      <div className="d-flex flex-wrap gap-2 mb-4 align-items-center">
        <button className={`admin-filter-chip ${!filterType ? 'active' : ''}`}
          onClick={() => setFilterType('')}>
          All <span className="admin-filter-count">{orgs.length}</span>
        </button>
        {ORG_TYPES.map(t => (
          <button key={t.value} className={`admin-filter-chip ${filterType === t.value ? 'active' : ''}`}
            onClick={() => setFilterType(filterType === t.value ? '' : t.value)}>
            {t.label} <span className="admin-filter-count">{typeCounts[t.value] || 0}</span>
          </button>
        ))}
        <div style={{ flex: 1 }} />
        <button className="admin-btn-primary" onClick={openCreate}>
          <Plus size={16} /> New Organization
        </button>
      </div>

      {/* Inline create/edit form — as modal */}
      {showForm && (
        <div className="admin-modal-overlay" onClick={() => setShowForm(false)}>
          <div className="admin-modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 520 }}>
            <div className="admin-modal-header">
              <h6 className="fw-bold m-0" style={{ color: 'var(--text-primary)' }}>
                {editingOrg ? <><Edit2 size={15} /> Edit Organization</> : <><Plus size={15} /> New Organization</>}
              </h6>
              <button className="btn p-0 border-0 bg-transparent d-flex" onClick={() => setShowForm(false)}>
                <X size={18} style={{ color: 'var(--text-muted)' }} />
              </button>
            </div>
            <div className="admin-modal-body">
              <form onSubmit={handleSubmit}>
                <div className="mb-3">
                  <label className="admin-form-label">Name</label>
                  <input className="admin-input" placeholder="Organization name" value={form.name}
                    onChange={e => setForm({ ...form, name: e.target.value })} required />
                </div>
                <div className="mb-3">
                  <label className="admin-form-label">Type</label>
                  <SearchableDropdown
                    className="sd-admin"
                    options={ORG_TYPES.map(t => ({ label: t.label, value: t.value }))}
                    value={form.org_type}
                    onChange={(val) => setForm({ ...form, org_type: val })}
                    placeholder="Select type..."
                    searchable={false}
                  />
                </div>
                <div className="d-flex gap-2 mt-4">
                  <button type="submit" className="admin-btn-primary flex-grow-1">
                    {editingOrg ? 'Update' : 'Create'}
                  </button>
                  <button type="button" className="admin-btn-ghost" onClick={() => setShowForm(false)}>
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Search */}
      <div className="admin-panel">
        <div className="admin-panel-header">
          <h6 className="admin-panel-title"><Building2 size={16} /> Organizations</h6>
          <div className="admin-search-bar" style={{ maxWidth: 280 }}>
            <Search size={15} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
            <input type="text" placeholder="Search organizations..." value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)} />
          </div>
        </div>
        <div className="admin-panel-body p-0">
          {/* Desktop table */}
          <div className="admin-table-scroll d-none d-md-block">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Type</th>
                  <th>Created</th>
                  <th style={{ width: 150 }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 ? (
                  <tr><td colSpan={4} className="text-center py-5" style={{ color: 'var(--text-muted)' }}>No organizations found</td></tr>
                ) : filtered.map(org => (
                  <tr key={org.id}>
                    <td>
                      <div className="d-flex align-items-center gap-2">
                        <div className="admin-org-icon">
                          {org.banner_url ? (
                            <img src={org.banner_url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: 'inherit' }} />
                          ) : (
                            <OrgLogo orgName={orgDisplayName(org.name)} size={32} />
                          )}
                        </div>
                        <div>
                          <div className="admin-cell-name">{orgDisplayName(org.name)}</div>
                          <div className="admin-cell-meta">ID: {org.id}</div>
                        </div>
                      </div>
                    </td>
                    <td><span className="admin-type-badge">{org.org_type}</span></td>
                    <td>
                      <span className="admin-cell-meta">{org.created_at ? new Date(org.created_at).toLocaleDateString() : '--'}</span>
                    </td>
                    <td>
                      <div className="d-flex gap-1">
                        <button className="admin-btn-sm primary" onClick={() => openEdit(org)} title="Edit">
                          <Edit2 size={14} />
                        </button>
                        <button className="admin-btn-sm" style={{ background: 'var(--warning-soft)', color: 'var(--warning)' }}
                          onClick={() => setApiKeyOrg(org)} title="API Keys">
                          <Key size={14} />
                        </button>
                        {!org.external_club_id && (
                          <button className="admin-btn-sm danger" title="Delete"
                            onClick={() => { setOrgToDelete(org); setDeleteModalOpen(true); }}>
                            <Trash2 size={14} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Mobile card list */}
          <div className="d-md-none admin-mobile-cards">
            {filtered.length === 0 ? (
              <div className="text-center py-5" style={{ color: 'var(--text-muted)' }}>No organizations found</div>
            ) : filtered.map(org => (
              <div key={org.id} className="admin-org-mobile-card">
                <div className="d-flex align-items-center gap-2 mb-2">
                  <div className="admin-org-icon">
                    {org.banner_url ? (
                      <img src={org.banner_url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: 'inherit' }} />
                    ) : (
                      <OrgLogo orgName={orgDisplayName(org.name)} size={32} />
                    )}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div className="admin-cell-name">{orgDisplayName(org.name)}</div>
                    <div className="admin-cell-meta">ID: {org.id}</div>
                  </div>
                  <span className="admin-type-badge">{org.org_type}</span>
                </div>
                <div className="d-flex gap-2">
                  <button className="admin-btn-sm primary flex-grow-1" onClick={() => openEdit(org)}>
                    <Edit2 size={13} /> Edit
                  </button>
                  <button className="admin-btn-sm flex-grow-1" style={{ background: 'var(--warning-soft)', color: 'var(--warning)' }}
                    onClick={() => setApiKeyOrg(org)}>
                    <Key size={13} /> Key
                  </button>
                  {!org.external_club_id && (
                    <button className="admin-btn-sm danger" title="Delete"
                      onClick={() => { setOrgToDelete(org); setDeleteModalOpen(true); }}>
                      <Trash2 size={13} />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>

          <div className="admin-table-footer">
            Showing {filtered.length} of {orgs.length} organizations
          </div>
        </div>
      </div>

      <ConfirmationModal isOpen={deleteModalOpen} onClose={() => setDeleteModalOpen(false)}
        onConfirm={handleDelete} title="Delete Organization"
        message={`Delete "${orgToDelete?.name}"? All associated roles and events will also be removed.`} />

      {apiKeyOrg && <ApiKeyModal org={apiKeyOrg} onClose={() => setApiKeyOrg(null)} />}
    </>
  );
};

// ─── ANALYTICS TAB ────────────────────────────────────────
const AnalyticsTab = ({ orgs }) => {
  const [selectedOrg, setSelectedOrg] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [loadingAnalytics, setLoadingAnalytics] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  const filteredOrgs = useMemo(() => {
    return orgs.filter(o => o.name.toLowerCase().includes(searchTerm.toLowerCase()));
  }, [orgs, searchTerm]);

  const fetchAnalytics = async (org) => {
    setSelectedOrg(org);
    setLoadingAnalytics(true);
    try {
      const res = await api.get(`/admin/orgs/${org.id}/analytics`);
      setAnalytics(res.data);
    } catch { toast.error("Failed to load analytics"); }
    setLoadingAnalytics(false);
  };

  const sortedDepts = analytics ? Object.entries(analytics.dept_analytics)
    .sort(([, a], [, b]) => b - a) : [];
  const maxDeptCount = sortedDepts.length > 0 ? sortedDepts[0][1] : 0;

  const analyticsContent = analytics ? (
    <>
      {/* Org header */}
      <div className="admin-analytics-header mb-4">
        <div>
          <h5 className="fw-bold mb-1" style={{ color: 'var(--text-primary)' }}>{orgDisplayName(analytics.org_name)}</h5>
          <span className="admin-type-badge">{analytics.org_type}</span>
        </div>
      </div>

      {/* Stat cards */}
      <div className="row g-3 mb-4">
        <div className="col-6 col-md-4">
          <div className="admin-stat-card">
            <div className="admin-stat-icon" style={{ background: 'var(--brand-primary-soft)', color: 'var(--brand-primary)' }}>
              <Calendar size={18} />
            </div>
            <div>
              <div className="admin-stat-value">{analytics.total_events}</div>
              <div className="admin-stat-label">Events</div>
            </div>
          </div>
        </div>
        <div className="col-6 col-md-4">
          <div className="admin-stat-card">
            <div className="admin-stat-icon" style={{ background: 'var(--success-soft)', color: 'var(--success)' }}>
              <TrendingUp size={18} />
            </div>
            <div>
              <div className="admin-stat-value">{analytics.total_registrations}</div>
              <div className="admin-stat-label">Registrations</div>
            </div>
          </div>
        </div>
        <div className="col-12 col-md-4">
          <div className="admin-stat-card">
            <div className="admin-stat-icon" style={{ background: 'var(--info-soft)', color: 'var(--info)' }}>
              <Users size={18} />
            </div>
            <div>
              <div className="admin-stat-value">{analytics.team?.length || 0}</div>
              <div className="admin-stat-label">Team Members</div>
            </div>
          </div>
        </div>
      </div>

      {/* Dept breakdown */}
      {sortedDepts.length > 0 && (
        <div className="admin-panel mb-4">
          <div className="admin-panel-header">
            <h6 className="admin-panel-title"><BarChart3 size={15} /> Department Registrations</h6>
          </div>
          <div className="admin-panel-body">
            <div className="admin-bar-chart">
              {sortedDepts.map(([dept, count]) => (
                <div key={dept} className="admin-bar-row">
                  <div className="admin-bar-label">{dept}</div>
                  <div className="admin-bar-track">
                    <div className="admin-bar-fill"
                      style={{ width: `${(count / maxDeptCount) * 100}%` }} />
                  </div>
                  <div className="admin-bar-value">{count}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Team list */}
      {analytics.team?.length > 0 && (
        <div className="admin-panel">
          <div className="admin-panel-header">
            <h6 className="admin-panel-title"><Users size={15} /> Team</h6>
          </div>
          <div className="admin-panel-body p-0">
            <table className="admin-table">
              <thead>
                <tr><th>Name</th><th>Email</th><th>Role</th></tr>
              </thead>
              <tbody>
                {analytics.team.map((m, i) => (
                  <tr key={i}>
                    <td className="admin-cell-name">{m.name}</td>
                    <td><span className="admin-cell-mono">{m.email}</span></td>
                    <td><span className="admin-type-badge">{m.role}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </>
  ) : null;

  return (
    <div className="row g-4">
      {/* Org selector */}
      <div className="col-12 col-md-4">
        <div className="admin-panel h-100">
          <div className="admin-panel-header">
            <h6 className="admin-panel-title"><Building2 size={16} /> Select Org</h6>
          </div>
          <div className="p-3">
            <div className="admin-search-bar mb-3" style={{ maxWidth: '100%' }}>
              <Search size={15} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
              <input type="text" placeholder="Filter..." value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)} />
            </div>
            <div className="admin-org-list">
              {filteredOrgs.map(org => (
                <button key={org.id}
                  className={`admin-org-item ${selectedOrg?.id === org.id ? 'active' : ''}`}
                  onClick={() => fetchAnalytics(org)}>
                  <div className="d-flex align-items-center gap-2" style={{ minWidth: 0 }}>
                    {org.banner_url ? (
                      <img src={org.banner_url} alt="" style={{ width: 24, height: 24, borderRadius: '50%', objectFit: 'cover', flexShrink: 0 }} />
                    ) : (
                      <OrgLogo orgName={orgDisplayName(org.name)} size={24} />
                    )}
                    <div style={{ minWidth: 0 }}>
                      <div className="admin-cell-name">{orgDisplayName(org.name)}</div>
                      <div className="admin-cell-meta">{org.org_type}</div>
                    </div>
                  </div>
                  <ChevronRight size={14} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Analytics display — desktop */}
      <div className="col-12 col-md-8 d-none d-md-block">
        {!selectedOrg ? (
          <div className="admin-panel">
            <div className="admin-panel-body">
              <div className="admin-empty-state" style={{ padding: '80px 24px'}}>
                <BarChart3 size={40} strokeWidth={1.5} />
                <p>Select an organization to view its analytics</p>
              </div>
            </div>
          </div>
        ) : loadingAnalytics ? (
          <div className="admin-panel">
            <div className="admin-panel-body d-flex justify-content-center py-5"><Loader /></div>
          </div>
        ) : analyticsContent}
      </div>

      {/* Analytics modal — mobile */}
      {selectedOrg && (
        <div className="admin-modal-overlay d-md-none" onClick={() => setSelectedOrg(null)}>
          <div className="admin-modal admin-modal-fullscreen" onClick={e => e.stopPropagation()}>
            <div className="admin-modal-header">
              <h6 className="fw-bold m-0" style={{ color: 'var(--text-primary)' }}>
                <BarChart3 size={16} style={{ marginRight: 6 }} /> Analytics
              </h6>
              <button className="btn p-0 border-0 bg-transparent d-flex" onClick={() => setSelectedOrg(null)}>
                <X size={18} style={{ color: 'var(--text-muted)' }} />
              </button>
            </div>
            <div className="admin-modal-body" style={{ maxHeight: '75vh', overflowY: 'auto' }}>
              {loadingAnalytics ? (
                <div className="d-flex justify-content-center py-5"><Loader /></div>
              ) : analyticsContent}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// ─── MAIN ADMIN DASHBOARD ─────────────────────────────────
const AdminDashboard = () => {
  const [activeTab, setActiveTab] = useState('users');
  const [users, setUsers] = useState([]);
  const [totalUsers, setTotalUsers] = useState(0);
  const [loadingMore, setLoadingMore] = useState(false);
  const [orgs, setOrgs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tabLoading, setTabLoading] = useState(false);
  const [loadedTabs, setLoadedTabs] = useState({});

  const fetchUsers = useCallback(async (skip = 0) => {
    try {
      const res = await api.get('/admin/users', { params: { skip, limit: 10 } });
      if (skip === 0) {
        setUsers(res.data.users);
      } else {
        setUsers(prev => [...prev, ...res.data.users]);
      }
      setTotalUsers(res.data.total);
    } catch { toast.error("Failed to load users"); }
  }, []);

  const fetchOrgs = useCallback(async () => {
    try {
      const res = await api.get('/admin/orgs');
      setOrgs(res.data);
    } catch { toast.error("Failed to load organizations"); }
  }, []);

  const loadMoreUsers = useCallback(async () => {
    if (loadingMore) return;
    setLoadingMore(true);
    await fetchUsers(users.length);
    setLoadingMore(false);
  }, [loadingMore, users.length, fetchUsers]);

  const hasMoreUsers = users.length < totalUsers;

  const fetchTabData = async (tab) => {
    if (loadedTabs[tab]) return;
    const isFirstLoad = Object.keys(loadedTabs).length === 0;
    if (isFirstLoad) setLoading(true); else setTabLoading(true);
    try {
      if (tab === 'users') {
        await fetchUsers(0);
      } else if (tab === 'orgs' || tab === 'analytics') {
        if (orgs.length === 0) await fetchOrgs();
      }
      setLoadedTabs(prev => ({ ...prev, [tab]: true }));
    } finally {
      setLoading(false);
      setTabLoading(false);
    }
  };

  useEffect(() => { fetchTabData(activeTab); }, [activeTab]);

  const handleRefresh = async () => {
    setLoadedTabs({});
    setUsers([]);
    setTotalUsers(0);
    setLoading(true);
    try {
      await fetchUsers(0);
      if (orgs.length > 0) await fetchOrgs();
      const newLoaded = { users: true };
      if (orgs.length > 0) { newLoaded.orgs = true; newLoaded.analytics = true; }
      setLoadedTabs(newLoaded);
    } finally { setLoading(false); }
  };

  if (loading && Object.keys(loadedTabs).length === 0) return <Loader />;

  return (
    <div className="container-fluid admin-dashboard">
      {/* Header */}
      <div className="admin-page-header">
        <div>
          <h2 className="admin-page-title">Admin Console</h2>
          <p className="admin-page-subtitle">Manage users, organizations, and view analytics</p>
        </div>
      </div>

      {/* Tab navigation */}
      <div className="admin-tab-bar mb-4">
        {TABS.map(tab => (
          <button key={tab.key}
            className={`admin-tab ${activeTab === tab.key ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.key)}>
            <tab.icon size={16} />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="fade-in" key={activeTab}>
        {tabLoading ? <Loader /> : (
          <>
            {activeTab === 'users' && (
              <UsersTab users={users} totalUsers={totalUsers} orgs={orgs}
                onRefresh={handleRefresh} onLoadMore={loadMoreUsers}
                loadingMore={loadingMore} hasMore={hasMoreUsers}
                onFetchOrgs={fetchOrgs} />
            )}
            {activeTab === 'orgs' && <OrgsTab orgs={orgs} onRefresh={handleRefresh} />}
            {activeTab === 'analytics' && <AnalyticsTab orgs={orgs} />}
          </>
        )}
      </div>
    </div>
  );
};

export default AdminDashboard;
