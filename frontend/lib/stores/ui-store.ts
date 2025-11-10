import { create } from 'zustand'

interface UiState {
  isSidebarCollapsed: boolean
  isMobileNavOpen: boolean
  toggleSidebar: () => void
  openSidebar: () => void
  closeSidebar: () => void
  toggleMobileNav: () => void
  closeMobileNav: () => void
}

export const useUiStore = create<UiState>((set) => ({
  isSidebarCollapsed: false,
  isMobileNavOpen: false,
  toggleSidebar: () =>
    set((state) => ({
      isSidebarCollapsed: !state.isSidebarCollapsed,
    })),
  openSidebar: () =>
    set(() => ({
      isSidebarCollapsed: false,
    })),
  closeSidebar: () =>
    set(() => ({
      isSidebarCollapsed: false,
    })),
  toggleMobileNav: () =>
    set((state) => ({
      isMobileNavOpen: !state.isMobileNavOpen,
    })),
  closeMobileNav: () =>
    set(() => ({
      isMobileNavOpen: false,
    })),
}))

