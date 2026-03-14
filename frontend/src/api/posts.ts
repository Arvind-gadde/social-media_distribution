import api from "./client";
import type { Post, Recommendation } from "../types";

export const createPost = (form: FormData) =>
  api.post<Post>("/posts", form, { headers: { "Content-Type": "multipart/form-data" } });

export const listPosts = (params?: { status?: string; limit?: number; offset?: number }) =>
  api.get<Post[]>("/posts", { params });

export const getPost = (id: string) => api.get<Post>(`/posts/${id}`);
export const retryPost = (id: string) => api.post<{ message: string }>(`/posts/${id}/retry`);
export const deletePost = (id: string) => api.delete(`/posts/${id}`);

export const getRecommendations = (mediaType: string, duration: number, language: string) =>
  api.get<{ recommendations: Recommendation[] }>("/posts/recommendations", {
    params: { media_type: mediaType, duration, language },
  });