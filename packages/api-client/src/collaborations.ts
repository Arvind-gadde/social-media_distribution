/**
 * Collaborations API Client
 * 
 * Handles brand deals, sponsorships, and collaborations
 */

import { getApiClient } from './client';
import type { PaginatedResponse } from './client';

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export interface Collaboration {
  id: string;
  user_id: string;
  type: string;
  brand_name?: string;
  brand_email?: string;
  brand_website?: string;
  contact_name?: string;
  contact_platform?: string;
  contact_handle?: string;
  title?: string;
  description?: string;
  deliverables?: any[];
  offered_amount?: number;
  negotiated_amount?: number;
  final_amount?: number;
  currency: string;
  payment_type?: string;
  payment_status: string;
  status: string;
  ai_score?: number;
  ai_recommendation?: string;
  source?: string;
  source_platform?: string;
  deal_starts_at?: string;
  deal_ends_at?: string;
  deadline_at?: string;
  notes?: string;
  internal_tags?: string[];
  metadata?: any;
  created_at: string;
  updated_at: string;
}

export interface CollaborationListParams {
  page?: number;
  page_size?: number;
  status?: string;
  type?: string;
  payment_status?: string;
  min_amount?: number;
  max_amount?: number;
}

export interface CollaborationCreate {
  type: string;
  brand_name?: string;
  brand_email?: string;
  contact_name?: string;
  title?: string;
  description?: string;
  offered_amount?: number;
  currency?: string;
  status?: string;
  deadline_at?: string;
}

export interface CollaborationUpdate {
  brand_name?: string;
  brand_email?: string;
  contact_name?: string;
  title?: string;
  description?: string;
  offered_amount?: number;
  negotiated_amount?: number;
  final_amount?: number;
  payment_status?: string;
  status?: string;
  notes?: string;
  deadline_at?: string;
}

export interface Contract {
  id: string;
  collaboration_id: string;
  user_id: string;
  contract_type: string;
  title?: string;
  content?: string;
  pdf_url?: string;
  status: string;
  signed_at?: string;
  expires_at?: string;
  signature_provider?: string;
  external_contract_id?: string;
  ai_review_summary?: string;
  ai_red_flags?: string[];
  created_at: string;
  updated_at: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// API FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * List collaborations with optional filtering
 */
export async function listCollaborations(
  params?: CollaborationListParams
): Promise<PaginatedResponse<Collaboration>> {
  const client = getApiClient();
  return await client.get<PaginatedResponse<Collaboration>>('/api/v1/collaborations', { params });
}

/**
 * Get single collaboration by ID
 */
export async function getCollaboration(id: string): Promise<Collaboration> {
  const client = getApiClient();
  return await client.get<Collaboration>(`/api/v1/collaborations/${id}`);
}

/**
 * Create new collaboration
 */
export async function createCollaboration(data: CollaborationCreate): Promise<Collaboration> {
  const client = getApiClient();
  return await client.post<Collaboration>('/api/v1/collaborations', data);
}

/**
 * Update collaboration
 */
export async function updateCollaboration(
  id: string,
  data: CollaborationUpdate
): Promise<Collaboration> {
  const client = getApiClient();
  return await client.patch<Collaboration>(`/api/v1/collaborations/${id}`, data);
}

/**
 * Delete collaboration
 */
export async function deleteCollaboration(id: string): Promise<void> {
  const client = getApiClient();
  await client.delete<void>(`/api/v1/collaborations/${id}`);
}

/**
 * Generate contract for collaboration
 */
export async function generateContract(collaborationId: string): Promise<Contract> {
  const client = getApiClient();
  return await client.post<Contract>(`/api/v1/collaborations/${collaborationId}/contract/generate`);
}

/**
 * Get contract for collaboration
 */
export async function getContract(collaborationId: string): Promise<Contract> {
  const client = getApiClient();
  return await client.get<Contract>(`/api/v1/collaborations/${collaborationId}/contract`);
}

/**
 * Update collaboration status
 */
export async function updateCollaborationStatus(
  id: string,
  status: string
): Promise<Collaboration> {
  const client = getApiClient();
  return await client.patch<Collaboration>(`/api/v1/collaborations/${id}/status`, { status });
}

/**
 * Get collaboration statistics
 */
export async function getCollaborationStats(): Promise<{
  total_active: number;
  total_completed: number;
  total_revenue: number;
  avg_deal_value: number;
  by_status: Record<string, number>;
  by_type: Record<string, number>;
}> {
  const client = getApiClient();
  return await client.get<{
    total_active: number;
    total_completed: number;
    total_revenue: number;
    avg_deal_value: number;
    by_status: Record<string, number>;
    by_type: Record<string, number>;
  }>('/api/v1/collaborations/stats');
}

