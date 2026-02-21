import Link from "next/link";
import { RegisterForm } from "@/components/auth/RegisterForm";
import { FileText, Sparkles, GitBranch, Shield } from "lucide-react";

export default function RegisterPage() {
  return (
    <main className="min-h-[calc(100vh-3.5rem)] grid lg:grid-cols-2">
      {/* Left decorative panel */}
      <div className="hidden lg:flex relative overflow-hidden gradient-primary items-center justify-center p-12">
        {/* Animated floating shapes */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute -top-20 -left-20 h-60 w-60 rounded-full bg-white/10 animate-pulse-soft" />
          <div className="absolute top-1/3 -right-10 h-40 w-40 rounded-full bg-white/5 animate-pulse-soft" style={{ animationDelay: '1s' }} />
          <div className="absolute -bottom-10 left-1/4 h-52 w-52 rounded-full bg-white/[0.07] animate-pulse-soft" style={{ animationDelay: '0.5s' }} />
          <div className="absolute top-10 right-1/3 h-24 w-24 rounded-full bg-white/10 animate-pulse-soft" style={{ animationDelay: '1.5s' }} />
        </div>

        <div className="relative z-10 max-w-md text-white">
          <div className="mb-8 flex h-16 w-16 items-center justify-center rounded-2xl bg-white/20 backdrop-blur-sm shadow-lg">
            <FileText className="h-8 w-8" />
          </div>
          <h2 className="text-3xl font-bold tracking-tight">PDF Agent</h2>
          <p className="mt-3 text-lg text-white/80">
            Your AI-powered document workspace for intelligent PDF editing and version management.
          </p>
          <div className="mt-10 space-y-4">
            {[
              { icon: Sparkles, text: "Natural language PDF editing" },
              { icon: GitBranch, text: "Full version control workflow" },
              { icon: Shield, text: "Secure & transparent operations" },
            ].map((item) => (
              <div key={item.text} className="flex items-center gap-3">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-white/15 backdrop-blur-sm">
                  <item.icon className="h-4 w-4" />
                </div>
                <span className="text-sm text-white/90">{item.text}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right form panel */}
      <div className="flex items-center justify-center bg-background p-6 sm:p-12">
        <div className="w-full max-w-sm animate-slide-up">
          {/* Mobile-only logo */}
          <div className="mb-8 text-center lg:hidden">
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl gradient-primary text-white shadow-lg">
              <FileText className="h-7 w-7" />
            </div>
          </div>

          <div className="mb-8">
            <h1 className="text-3xl font-bold tracking-tight">Get started</h1>
            <p className="mt-2 text-muted-foreground">Create your account in seconds</p>
          </div>

          <RegisterForm />

          <div className="mt-8 text-center">
            <p className="text-sm text-muted-foreground">
              Already have an account?{" "}
              <Link className="font-semibold text-primary hover:text-primary/80 transition-colors" href="/auth/login">
                Sign in
              </Link>
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}
