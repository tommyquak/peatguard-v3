"use client";
// W1 · Login + workspace switcher.
// Source: design_handoff_peatguard/web-screens-1.jsx:94-142.

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Eye, Info, Lock, Mail, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { Btn } from "@/components/ui/Btn";
import { Input } from "@/components/ui/Input";
import { Logomark } from "@/components/ui/Logomark";
import { MapStub } from "@/components/ui/MapStub";
import { useLogin } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const login = useLogin();
  const [email, setEmail] = useState("tommy.quak@peatguard.id");
  const [password, setPassword] = useState("••••••••••••");

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      await login.mutateAsync({ email, password });
      toast.success("Welcome back");
      router.push("/dashboard");
    } catch (err: any) {
      toast.error(err.message || "Sign-in failed");
    }
  }

  return (
    <div className="grid grid-cols-2 h-screen bg-pg-surface overflow-hidden">
      <div className="relative overflow-hidden">
        <MapStub
          layer="canal_risk · Sebangau, Central Kalimantan"
          bg="/aoi-satellite.png"
          overlay="/aoi-classified.png"
          overlayOpacity={0.55}
          full
          className="h-full"
        >
          <div
            className="absolute inset-0"
            style={{ background: "linear-gradient(135deg, rgba(31,77,58,0.85), rgba(61,40,24,0.55))" }}
          />
          <div className="absolute left-14 top-14 text-white flex items-center gap-3">
            <Logomark size={36} />
            <span className="text-lg font-bold tracking-tight">PeatGuard</span>
          </div>
          <div className="absolute left-14 bottom-14 right-14 text-white">
            <div className="text-xs font-mono opacity-75 mb-3.5 uppercase tracking-wider">
              Indonesia · Kalimantan · Sumatra
            </div>
            <h1
              className="text-[38px] font-semibold leading-tight max-w-[420px]"
              style={{ letterSpacing: "-0.025em" }}
            >
              From satellite radar to canal blocks that actually get built.
            </h1>
            <p className="text-base opacity-80 mt-3.5 max-w-[380px] leading-relaxed">
              Operator dashboard for restoration agencies, NGOs and forestry desks. Turn priority
              maps into paid restoration tasks.
            </p>
          </div>
        </MapStub>
      </div>
      <form onSubmit={onSubmit} className="grid place-items-center p-14">
        <div className="w-[380px]">
          <div className="text-xs font-semibold text-pg-primary uppercase tracking-widest mb-3">
            Sign in
          </div>
          <h2 className="text-[28px] font-semibold tracking-tight mb-1.5">Welcome back</h2>
          <p className="text-base text-pg-ink-secondary mb-7">
            PeatGuard team sign-in. SSO available for partner agencies.
          </p>
          <div className="flex flex-col gap-3.5">
            <Input
              label="Work email"
              icon={<Mail size={16} />}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              type="email"
            />
            <Input
              label="Password"
              icon={<Lock size={16} />}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              type="password"
              trailing={<Eye size={16} className="text-pg-ink-muted" />}
            />
            <div className="flex justify-between text-[12.5px] mt-1">
              <label className="flex items-center gap-1.5 text-pg-ink-secondary">
                <span className="w-3.5 h-3.5 rounded-[3px] bg-pg-primary grid place-items-center">
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3">
                    <path d="M4 12l5 5 11-12" />
                  </svg>
                </span>
                Remember this device
              </label>
              <a href="#" className="text-pg-primary font-semibold no-underline">
                Forgot password?
              </a>
            </div>
            <Btn kind="primary" size="lg" full type="submit" className="mt-1.5" disabled={login.isPending}>
              {login.isPending ? "Signing in…" : "Sign in"}
            </Btn>
            <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2.5 text-pg-ink-muted text-[11.5px] my-1.5">
              <div className="h-px bg-pg-border" />
              OR
              <div className="h-px bg-pg-border" />
            </div>
            <Btn
              kind="secondary"
              size="lg"
              full
              type="button"
              icon={<ShieldCheck size={16} />}
            >
              Partner SSO (BRGM, WWF-ID, KLHK)
            </Btn>
          </div>
          <div className="mt-7 p-3.5 bg-pg-primary-soft rounded-md text-xs text-pg-primary flex items-start gap-2.5">
            <Info size={16} className="shrink-0 mt-0.5" />
            <span>
              Your PeatGuard account manages <b>3 partner programmes</b>. Pick one after sign-in.
            </span>
          </div>
        </div>
      </form>
    </div>
  );
}
