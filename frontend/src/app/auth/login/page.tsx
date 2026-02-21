import Link from "next/link";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { LoginForm } from "@/components/auth/LoginForm";
import { Sparkles, GitBranch, Shield } from "lucide-react";

export default function LoginPage() {
  return (
    <main className="min-h-[calc(100vh-3.5rem)] gradient-hero">
      <div className="mx-auto grid max-w-6xl items-center gap-8 px-4 py-12 md:grid-cols-2 md:py-20">
        <Card className="animate-slide-up gradient-card border-primary/10 shadow-sm">
          <CardHeader>
            <CardTitle className="text-2xl">Welcome back</CardTitle>
            <CardDescription>Continue editing documents and managing draft versions.</CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-3 stagger-children">
              {[
                { icon: Sparkles, text: "Run natural language PDF commands", color: "text-primary bg-primary/10" },
                { icon: GitBranch, text: "Track every draft and tool execution", color: "text-accent-foreground bg-accent" },
                { icon: Shield, text: "Accept only final approved versions", color: "text-[oklch(0.45_0.18_310)] bg-[oklch(0.93_0.05_310)]" },
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
          <LoginForm />
          <p className="text-center text-sm text-muted-foreground">
            No account?{" "}
            <Link className="font-medium text-primary underline underline-offset-4 hover:text-primary/80 transition-colors" href="/auth/register">
              Register
            </Link>
          </p>
        </div>
      </div>
    </main>
  );
}
