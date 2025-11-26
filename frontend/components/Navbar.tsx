'use client';

import { signOut, useSession } from 'next-auth/react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { HomeIcon, LineChartIcon, TrendingUpIcon, WalletIcon, LogOutIcon } from 'lucide-react';

export default function Navbar() {
  const { data: session } = useSession();
  const pathname = usePathname();

  const navItems = [
    { href: '/', label: 'Dashboard', icon: HomeIcon },
    { href: '/opportunities', label: 'Opportunités', icon: TrendingUpIcon },
    { href: '/bets', label: 'Paris', icon: WalletIcon },
    { href: '/agents-comparison', label: 'Comparaison Agents', icon: LineChartIcon },
    { href: '/analytics', label: 'Analytics', icon: LineChartIcon },
    { href: '/full-gain', label: 'Full Gain 2.0', icon: TrendingUpIcon },
  ];

  return (
    <nav className="bg-dark text-white border-b border-gray-700">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center">
            <Link href="/dashboard" className="flex items-center">
              <span className="text-2xl font-bold text-primary">Mon_PS</span>
            </Link>
            <div className="hidden md:block ml-10">
              <div className="flex items-baseline space-x-4">
                {navItems.map((item) => {
                  const Icon = item.icon;
                  const isActive = pathname === item.href;
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={`px-3 py-2 rounded-md text-sm font-medium flex items-center gap-2 transition-colors ${
                        isActive
                          ? 'bg-primary text-white'
                          : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                      }`}
                    >
                      <Icon size={18} />
                      {item.label}
                    </Link>
                  );
                })}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-300">{session?.user?.name}</span>
            <button
              onClick={() => signOut({ callbackUrl: '/login' })}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-danger rounded-md hover:bg-red-600 transition-colors"
            >
              <LogOutIcon size={18} />
              Déconnexion
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}
