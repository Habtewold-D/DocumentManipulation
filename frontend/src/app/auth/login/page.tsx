import Link from "next/link";
import { LoginForm } from "@/components/auth/LoginForm";

export default function LoginPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-5xl items-center justify-center px-4">
      <div className="space-y-4">
        <LoginForm />
        <p className="text-center text-sm text-muted-foreground">
          No account? <Link className="underline" href="/auth/register">Register</Link>
        </p>
      </div>
    </main>
  );
}
