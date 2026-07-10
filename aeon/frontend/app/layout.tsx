export const metadata = { title: "AEON", description: "Adverse Event Orchestration Nexus" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
