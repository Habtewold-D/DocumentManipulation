import Link from "next/link";
import { RegisterForm } from "@/components/auth/RegisterForm";

export default function RegisterPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-5xl items-center justify-center px-4">
      <div className="space-y-4">
        <RegisterForm />
        <p className="text-center text-sm text-muted-foreground">
          Already have an account? <Link className="underline" href="/auth/login">Sign in</Link>
        </p>
      </div>
    </main>
  );
}
