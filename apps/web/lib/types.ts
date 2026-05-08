// Wire types matching peatguard.api.schemas. Hand-maintained because the
// project doesn't yet have an OpenAPI -> TS codegen step.

export type TaskStatus =
  | "available"
  | "accepted"
  | "submitted"
  | "approved"
  | "rejected"
  | "paid";

export type TaskType = "canal_block" | "revegetation" | "patrol" | "fire_watch";

export interface User {
  email: string;
  name: string;
  role: "operator" | "villager";
}

export interface Aoi {
  code: string;
  name: string;
  risk: number;
  pct_critical: number;
  refresh_date: string;
  progress_pct: number;
  restored_ha: number;
  area_ha: number;
  center_lat: number;
  center_lng: number;
}

export interface Worker {
  id: string;
  name: string;
  village: string | null;
  nik_verified: boolean;
  rating: number;
  role: string | null;
  total_paid: number;
  completion_rate: number;
  tasks_done: number;
  flag: string | null;
}

export interface Photo {
  id: number;
  phase: "before" | "during" | "after";
  ts: number;
  lat: number;
  lng: number;
  accuracy_m: number;
  sha256: string;
  prev_sha256: string | null;
}

export interface Task {
  id: string;
  aoi_code: string;
  village_id: string | null;
  type: string;
  title: string;
  sub: string | null;
  payout_idr: number;
  deadline: string;
  status: TaskStatus;
  worker_id: string | null;
  deliverables: string[];
  rail: string | null;
  arrived: { lat: number; lng: number; acc: number } | null;
  arrived_at: string | null;
  submitted_at: string | null;
  decided_at: string | null;
  decision_note: string | null;
  created_at: string;
  photos: Photo[];
  polygon: GeoJSONPolygon | null;
}

export interface GeoJSONPolygon {
  type: "Polygon";
  coordinates: number[][][];
}

export interface Payment {
  id: string;
  task_id: string;
  worker_id: string;
  worker_name: string | null;
  task_title: string | null;
  amount: number;
  rail: string;
  status: "pending" | "released" | "disputed";
  flag: string | null;
  created_at: string;
  released_at: string | null;
}

export interface Message {
  id: number;
  task_id: string;
  sender: string;
  body: string;
  kind: "user" | "operator" | "system";
  attach: string | null;
  created_at: string;
}

export interface Village {
  id: string;
  name: string;
  aoi_code: string;
  lat: number;
  lng: number;
}
