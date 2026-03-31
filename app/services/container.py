from app.config import get_settings
from app.services.analytics import AnalyticsService
from app.services.alerts import AlertsService
from app.services.billing import BillingService
from app.services.market import MarketDataProvider
from app.services.portfolio import PortfolioService
from app.services.repository import Repository
from app.services.rocket import RocketService
from app.services.subscriptions import SubscriptionService


settings = get_settings()
repository = Repository(settings.database_path)
market_provider = MarketDataProvider(repository=repository)
analytics_service = AnalyticsService(market_provider=market_provider)
billing_service = BillingService(repository=repository)
subscription_service = SubscriptionService(repository=repository)
portfolio_service = PortfolioService(repository=repository)
alerts_service = AlertsService(repository=repository)
rocket_service = RocketService(repository=repository)
