"use client";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/lib/authStore";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const token = useAuth((s) => s.token);

  useEffect(() => {
    if (!token) router.replace("/");
  }, [token, router]);

  if (!token) return null;
  return <>{children}</>;
}
