import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Sparkles, GitBranch, FileSearch, ArrowRight, FileText } from "lucide-react";

export default function Home() {
  return (
    <main className="min-h-[calc(100vh-3.5rem)] gradient-hero">
      <div className="mx-auto max-w-6xl px-4 py-12 md:py-20">
        {/* Hero Section */}
        <section className="animate-fade-in text-center mb-12 md:mb-16">
          <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-2xl gradient-primary text-white shadow-lg">
            <FileText className="h-8 w-8" />
          </div>
          <p className="mb-3 text-sm font-medium uppercase tracking-widest text-primary">
            AI-Powered Document Workspace
          </p>
          <h1 className="text-4xl font-bold tracking-tight md:text-5xl lg:text-6xl">
            Edit PDFs with
            <span className="block bg-gradient-to-r from-primary to-[oklch(0.58_0.22_295)] bg-clip-text text-transparent">
              Natural Language
            </span>
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-lg text-muted-foreground">
            Upload, edit, version, and compare PDFs using natural-language commands backed by MCP tools.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
            <Button asChild size="lg" className="gradient-primary border-0 text-white shadow-md hover:shadow-lg transition-all gap-2 px-8">
              <Link href="/auth/register">
                Get Started
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
            <Button asChild variant="outline" size="lg" className="gap-2 px-8 border-primary/30 hover:bg-primary/5">
              <Link href="/auth/login">Sign in</Link>
            </Button>
          </div>
        </section>

        {/* Feature Pills */}
        <section className="animate-slide-up mb-12 md:mb-16">
          <div className="grid gap-4 sm:grid-cols-3 stagger-children">
            <Card className="animate-fade-in gradient-card border-primary/10 shadow-sm hover:shadow-md transition-all hover:-translate-y-0.5">
              <CardContent className="flex items-start gap-4 p-5">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                  <Sparkles className="h-5 w-5" />
                </div>
                <div>
                  <p className="font-semibold">Natural Language Editing</p>
                  <p className="mt-1 text-sm text-muted-foreground">Describe changes in plain English and let AI handle the PDF manipulation.</p>
                </div>
              </CardContent>
            </Card>
            <Card className="animate-fade-in gradient-card border-primary/10 shadow-sm hover:shadow-md transition-all hover:-translate-y-0.5">
              <CardContent className="flex items-start gap-4 p-5">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-accent text-accent-foreground">
                  <GitBranch className="h-5 w-5" />
                </div>
                <div>
                  <p className="font-semibold">Version Control Workflow</p>
                  <p className="mt-1 text-sm text-muted-foreground">Draft, review, accept, or reject every change with a complete history.</p>
                </div>
              </CardContent>
            </Card>
            <Card className="animate-fade-in gradient-card border-primary/10 shadow-sm hover:shadow-md transition-all hover:-translate-y-0.5">
              <CardContent className="flex items-start gap-4 p-5">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[oklch(0.93_0.05_310)] text-[oklch(0.45_0.18_310)]">
                  <FileSearch className="h-5 w-5" />
                </div>
                <div>
                  <p className="font-semibold">Page-Level Comparison</p>
                  <p className="mt-1 text-sm text-muted-foreground">Visually compare any two accepted versions page by page.</p>
                </div>
              </CardContent>
            </Card>
          </div>
        </section>

        {/* How it works */}
        <section className="animate-slide-up">
          <Card className="gradient-card border-primary/10 shadow-sm">
            <CardHeader className="text-center">
              <CardTitle className="text-2xl">How it works</CardTitle>
              <CardDescription className="text-base">Simple flow from upload to approved output.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="mx-auto grid max-w-3xl gap-4 sm:grid-cols-3 stagger-children">
                {[
                  { step: "1", title: "Upload", desc: "Upload a PDF from your dashboard" },
                  { step: "2", title: "Edit", desc: "Run edit commands in the document workspace" },
                  { step: "3", title: "Review", desc: "Review draft versions and accept or reject" },
                ].map((item) => (
                  <div key={item.step} className="animate-fade-in flex flex-col items-center text-center p-4">
                    <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full gradient-primary text-white text-lg font-bold shadow-md">
                      {item.step}
                    </div>
                    <p className="font-semibold">{item.title}</p>
                    <p className="mt-1 text-sm text-muted-foreground">{item.desc}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </section>
      </div>
    </main>
  );
}
