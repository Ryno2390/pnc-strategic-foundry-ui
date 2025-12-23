import SwiftUI

/// Executive Profile Sidebar with stats grid and enrolled products
struct ProfileSidebar: View {
    let profile: ExecutiveProfile
    let notifications: [AppNotification]
    @Binding var aiMode: AIProcessingMode
    let onStatTapped: (ProfileStat) -> Void
    let onNotificationTapped: (AppNotification) -> Void
    let onClose: () -> Void

    private var unreadCount: Int {
        notifications.filter { !$0.isRead }.count
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Header
            sidebarHeader

            ScrollView {
                VStack(alignment: .leading, spacing: PNCTheme.Spacing.lg) {
                    // Profile Info
                    profileSection

                    Divider()
                        .background(PNCTheme.Colors.darkGrey.opacity(0.2))

                    // Stats Grid
                    statsSection

                    // Enrolled Products
                    if !profile.enrolledProducts.isEmpty {
                        Divider()
                            .background(PNCTheme.Colors.darkGrey.opacity(0.2))
                        enrolledProductsSection
                    }

                    Divider()
                        .background(PNCTheme.Colors.darkGrey.opacity(0.2))

                    // Message Center
                    messageCenterSection
                }
                .padding(PNCTheme.Spacing.lg)
            }

            // AI Mode Toggle - Fixed at bottom
            aiModeToggle
        }
        .frame(width: 320)
        .background(PNCTheme.Colors.white)
        .shadow(color: .black.opacity(0.15), radius: 10, x: 5, y: 0)  // Shadow on right side
    }

    // MARK: - Header

    private var sidebarHeader: some View {
        HStack {
            Text("EXECUTIVE PORTAL")
                .font(.system(size: 12, weight: .bold))
                .foregroundColor(PNCTheme.Colors.white)
                .kerning(2)

            Spacer()

            Button(action: onClose) {
                Image(systemName: "xmark")
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundColor(PNCTheme.Colors.white)
                    .frame(width: 28, height: 28)
            }
            .buttonStyle(.plain)
            .pncHoverEffect(showBorder: false, scale: 1.1)
        }
        .padding(PNCTheme.Spacing.md)
        .background(PNCTheme.Colors.darkGrey)
    }

    // MARK: - Profile Section

    private var profileSection: some View {
        VStack(alignment: .leading, spacing: PNCTheme.Spacing.sm) {
            HStack(spacing: PNCTheme.Spacing.md) {
                // Profile Avatar
                ZStack {
                    Circle()
                        .fill(PNCTheme.Colors.orange)
                        .frame(width: 50, height: 50)
                    Text("MM")
                        .font(.system(size: 18, weight: .bold))
                        .foregroundColor(.white)
                }

                VStack(alignment: .leading, spacing: 2) {
                    Text(profile.customerId)
                        .font(.system(size: 12, weight: .medium))
                        .foregroundColor(PNCTheme.Colors.orange)
                    Text(profile.organization)
                        .font(.system(size: 11))
                        .foregroundColor(PNCTheme.Colors.textSecondary)
                        .lineLimit(2)
                }
            }
        }
    }

    // MARK: - Stats Section

    private var statsSection: some View {
        VStack(alignment: .leading, spacing: PNCTheme.Spacing.md) {
            Text("STRATEGIC METRICS")
                .font(.system(size: 10, weight: .bold))
                .foregroundColor(PNCTheme.Colors.textSecondary)
                .kerning(1)

            LazyVGrid(columns: [
                GridItem(.flexible(), spacing: PNCTheme.Spacing.sm),
                GridItem(.flexible(), spacing: PNCTheme.Spacing.sm)
            ], spacing: PNCTheme.Spacing.sm) {
                ForEach(profile.stats) { stat in
                    StatCard(stat: stat, onTap: { onStatTapped(stat) })
                }
            }
        }
    }

    // MARK: - Enrolled Products Section

    private var enrolledProductsSection: some View {
        VStack(alignment: .leading, spacing: PNCTheme.Spacing.md) {
            Text("ENROLLED PRODUCTS")
                .font(.system(size: 10, weight: .bold))
                .foregroundColor(PNCTheme.Colors.textSecondary)
                .kerning(1)

            ForEach(profile.enrolledProducts) { product in
                EnrolledProductRow(product: product)
            }
        }
    }

    // MARK: - Message Center Section

    private var messageCenterSection: some View {
        VStack(alignment: .leading, spacing: PNCTheme.Spacing.md) {
            HStack {
                Text("MESSAGE CENTER")
                    .font(.system(size: 10, weight: .bold))
                    .foregroundColor(PNCTheme.Colors.textSecondary)
                    .kerning(1)

                Spacer()

                if unreadCount > 0 {
                    Text("\(unreadCount)")
                        .font(.system(size: 10, weight: .bold))
                        .foregroundColor(.white)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(PNCTheme.Colors.orange)
                        .clipShape(Capsule())
                }
            }

            ForEach(notifications) { notification in
                NotificationRow(notification: notification) {
                    onNotificationTapped(notification)
                }
            }
        }
    }

    // MARK: - AI Mode Toggle

    private var aiModeToggle: some View {
        VStack(spacing: 0) {
            Divider()
                .background(PNCTheme.Colors.darkGrey.opacity(0.3))

            VStack(alignment: .leading, spacing: PNCTheme.Spacing.sm) {
                Text("AI PROCESSING MODE")
                    .font(.system(size: 9, weight: .bold))
                    .foregroundColor(PNCTheme.Colors.textSecondary)
                    .kerning(1)

                // Toggle Button
                HStack(spacing: 0) {
                    ForEach(AIProcessingMode.allCases, id: \.self) { mode in
                        Button(action: {
                            withAnimation(.easeInOut(duration: 0.2)) {
                                aiMode = mode
                            }
                        }) {
                            HStack(spacing: 6) {
                                Image(systemName: mode.icon)
                                    .font(.system(size: 11))
                                VStack(alignment: .leading, spacing: 1) {
                                    Text(mode.rawValue)
                                        .font(.system(size: 10, weight: .bold))
                                    Text(mode.description)
                                        .font(.system(size: 8))
                                        .opacity(0.8)
                                }
                            }
                            .foregroundColor(aiMode == mode ? .white : PNCTheme.Colors.darkGrey)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 10)
                            .padding(.horizontal, 8)
                            .background(
                                aiMode == mode
                                    ? (mode == .onDevice ? PNCTheme.Colors.darkGrey : PNCTheme.Colors.orange)
                                    : PNCTheme.Colors.lightGrey
                            )
                        }
                        .buttonStyle(.plain)
                    }
                }

                // Status indicator
                HStack(spacing: 6) {
                    Circle()
                        .fill(aiMode == .onDevice ? Color.green : PNCTheme.Colors.orange)
                        .frame(width: 6, height: 6)
                    Text(aiMode == .onDevice ? "Processing locally on Apple Silicon" : "Connected to PNC Enterprise Cloud")
                        .font(.system(size: 9))
                        .foregroundColor(PNCTheme.Colors.textSecondary)
                }
            }
            .padding(PNCTheme.Spacing.md)
            .background(PNCTheme.Colors.lightGrey.opacity(0.5))
        }
    }
}

// MARK: - Stat Card

struct StatCard: View {
    let stat: ProfileStat
    let onTap: () -> Void

    var body: some View {
        Button(action: onTap) {
            VStack(alignment: .leading, spacing: 6) {
                Image(systemName: stat.icon)
                    .font(.system(size: 16))
                    .foregroundColor(PNCTheme.Colors.orange)

                Text(stat.value)
                    .font(.system(size: 18, weight: .bold))
                    .foregroundColor(PNCTheme.Colors.darkGrey)

                Text(stat.label)
                    .font(.system(size: 9, weight: .medium))
                    .foregroundColor(PNCTheme.Colors.textSecondary)
                    .kerning(0.5)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(PNCTheme.Spacing.sm)
            .background(PNCTheme.Colors.lightGrey.opacity(0.5))
        }
        .buttonStyle(.plain)
        .pncHoverEffect(scale: 1.03)
    }
}

// MARK: - Enrolled Product Row

struct EnrolledProductRow: View {
    let product: EnrolledProduct

    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 2) {
                Text(product.name)
                    .font(.system(size: 12, weight: .medium))
                    .foregroundColor(PNCTheme.Colors.darkGrey)
                Text(product.value)
                    .font(.system(size: 14, weight: .bold))
                    .foregroundColor(PNCTheme.Colors.darkGrey)
            }

            Spacer()

            Text(product.status.rawValue)
                .font(.system(size: 9, weight: .semibold))
                .foregroundColor(.white)
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(Color.green)
        }
        .padding(PNCTheme.Spacing.sm)
        .background(PNCTheme.Colors.lightGrey.opacity(0.5))
    }
}

// MARK: - Notification Row

struct NotificationRow: View {
    let notification: AppNotification
    let onTap: () -> Void

    private var iconColor: Color {
        switch notification.type {
        case .approval: return .green
        case .info: return .blue
        case .alert: return PNCTheme.Colors.orange
        }
    }

    var body: some View {
        Button(action: onTap) {
            HStack(alignment: .top, spacing: PNCTheme.Spacing.sm) {
                Image(systemName: notification.type.icon)
                    .font(.system(size: 14))
                    .foregroundColor(iconColor)

                VStack(alignment: .leading, spacing: 2) {
                    HStack {
                        Text(notification.title)
                            .font(.system(size: 11, weight: notification.isRead ? .medium : .bold))
                            .foregroundColor(PNCTheme.Colors.darkGrey)

                        if !notification.isRead {
                            Circle()
                                .fill(PNCTheme.Colors.orange)
                                .frame(width: 6, height: 6)
                        }
                    }

                    Text(notification.message)
                        .font(.system(size: 10))
                        .foregroundColor(PNCTheme.Colors.textSecondary)
                        .lineLimit(2)
                }

                Spacer()
            }
            .padding(PNCTheme.Spacing.sm)
        }
        .buttonStyle(.plain)
        .pncHoverEffect(scale: 1.01)
    }
}

#Preview {
    @Previewable @State var aiMode: AIProcessingMode = .onDevice
    ProfileSidebar(
        profile: .default,
        notifications: AppNotification.defaultNotifications,
        aiMode: $aiMode,
        onStatTapped: { _ in },
        onNotificationTapped: { _ in },
        onClose: {}
    )
}
