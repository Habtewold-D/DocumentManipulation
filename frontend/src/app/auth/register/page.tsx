import Link from "next/link";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { RegisterForm } from "@/components/auth/RegisterForm";
import { Shield, Cloud, ScrollText } from "lucide-react";

export default function RegisterPage() {
  return (
    <main className="min-h-[calc(100vh-3.5rem)] gradient-hero">
      <div className="mx-auto grid max-w-6xl items-center gap-8 px-4 py-12 md:grid-cols-2 md:py-20">
        <Card className="animate-slide-up gradient-card border-primary/10 shadow-sm">
          <CardHeader>
            <CardTitle className="text-2xl">Create your workspace</CardTitle>
            <CardDescription>Set up your account and start document workflows in minutes.</CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-3 stagger-children">
              {[
                { icon: Shield, text: "Secure authentication with JWT sessions", color: "text-primary bg-primary/10" },
                { icon: Cloud, text: "Cloud-hosted PDF assets and version history", color: "text-accent-foreground bg-accent" },
                { icon: ScrollText, text: "Tool logs for transparent operations", color: "text-[oklch(0.45_0.18_310)] bg-[oklch(0.93_0.05_310)]" },
              ].map((item) => (
                <li key={item.text} className="animate-fade-in flex items-center gap-3 rounded-lg border border-primary/10 bg-card p-3.5 text-sm">
                  <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${item.color}`}>
                    <item.icon className="h-4 w-4" />
                  </div>
                  <span className="text-foreground">{item.text}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>

        <div className="space-y-4">
          <RegisterForm />
          <p className="text-center text-sm text-muted-foreground">
            Already have an account?{" "}
            <Link className="font-medium text-primary underline underline-offset-4 hover:text-primary/80 transition-colors" href="/auth/login">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </main>
  );
}
