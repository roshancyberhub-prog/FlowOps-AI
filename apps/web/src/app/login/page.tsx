"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ArrowRight, GitBranch, ShieldCheck } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";

const schema = z.object({
  email: z.email("Enter a valid email address."),
  password: z.string().min(12, "Use at least 12 characters.").max(128),
  display_name: z.string().max(100).optional(),
});
type Fields = z.infer<typeof schema>;

export default function Login() {
  const [register, setRegister] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();
  const client = useQueryClient();
  const form = useForm<Fields>({ resolver: zodResolver(schema) });
  const submit = form.handleSubmit(async (data) => {
    setError("");
    try {
      if (register)
        await api("/auth/register", {
          method: "POST",
          body: JSON.stringify(data),
        });
      await api("/auth/session/login", {
        method: "POST",
        body: new URLSearchParams({
          username: data.email,
          password: data.password,
        }),
      });
      client.clear();
      router.replace("/");
    } catch (error) {
      setError(error instanceof Error ? error.message : "Unable to sign in.");
    }
  });
  return (
    <main className="grid min-h-screen lg:grid-cols-2">
      <section className="relative hidden flex-col justify-between overflow-hidden bg-slate-950 p-14 text-white lg:flex">
        <div className="flex items-center gap-3 text-xl font-semibold">
          <span className="rounded-xl bg-teal-500 p-2 text-slate-950">
            <GitBranch size={24} />
          </span>
          FlowOps <span className="text-teal-300">AI</span>
        </div>
        <div className="relative z-10 max-w-lg">
          <p className="mb-5 text-xs font-semibold uppercase tracking-[.2em] text-teal-300">
            Your operations, connected
          </p>
          <h1 className="text-5xl font-semibold leading-tight tracking-tight">
            Less busywork.
            <br />
            More forward motion.
          </h1>
          <p className="mt-6 max-w-sm text-base leading-7 text-slate-400">
            Bring your leads and operations into one focused workspace. Build a
            reliable foundation for every follow-up.
          </p>
          <div className="mt-10 flex items-center gap-3 text-sm text-slate-300">
            <ShieldCheck className="text-teal-300" size={20} />
            Organization-scoped access. You stay in control.
          </div>
        </div>
        <p className="text-xs text-slate-500">
          FlowOps AI · Operations workspace
        </p>
        <div
          aria-hidden
          className="absolute -right-28 bottom-8 h-96 w-96 rounded-full border border-teal-900/50"
        />
      </section>
      <section className="flex items-center justify-center bg-white px-6 py-12">
        <div className="w-full max-w-sm">
          <div className="mb-12 flex items-center gap-2 text-xl font-bold lg:hidden">
            <GitBranch className="text-teal-700" />
            FlowOps AI
          </div>
          <p className="eyebrow mb-3">Get things moving</p>
          <h2 className="text-3xl font-semibold tracking-tight">
            {register ? "Create your account" : "Welcome back"}
          </h2>
          <p className="mb-8 mt-3 text-slate-500">
            {register
              ? "Your workspace starts here."
              : "Sign in to your operations workspace."}
          </p>
          <form onSubmit={submit} className="space-y-5">
            {register && (
              <div>
                <label htmlFor="display_name">Full name</label>
                <input
                  id="display_name"
                  autoComplete="name"
                  required
                  {...form.register("display_name")}
                />
              </div>
            )}
            <div>
              <label htmlFor="email">Work email</label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                required
                placeholder="you@company.com"
                {...form.register("email")}
              />
              {form.formState.errors.email && (
                <p className="field-error">
                  {form.formState.errors.email.message}
                </p>
              )}
            </div>
            <div>
              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                autoComplete={register ? "new-password" : "current-password"}
                required
                minLength={12}
                maxLength={128}
                {...form.register("password")}
              />
              <p className="mt-2 text-xs text-slate-500">
                Use 12–128 characters.
              </p>
              {form.formState.errors.password && (
                <p className="field-error">
                  {form.formState.errors.password.message}
                </p>
              )}
            </div>
            {error && (
              <div role="alert" className="notice">
                {error}
              </div>
            )}
            <Button className="w-full" disabled={form.formState.isSubmitting}>
              {form.formState.isSubmitting
                ? "Please wait…"
                : register
                  ? "Create account"
                  : "Sign in"}
              <ArrowRight size={16} />
            </Button>
          </form>
          <p className="mt-7 text-center text-sm text-slate-500">
            {register ? "Already have an account?" : "New to FlowOps?"}{" "}
            <button
              type="button"
              className="ml-1 font-semibold text-teal-800 underline-offset-4 hover:underline"
              onClick={() => {
                setRegister(!register);
                setError("");
                form.clearErrors();
              }}
            >
              {register ? "Sign in" : "Create an account"}
            </button>
          </p>
        </div>
      </section>
    </main>
  );
}
