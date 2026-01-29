class OpenAIAzureService(OpenAIClient):
    def __init__(
        self,
        deployment_name: str,
        api_version: str,
        azure_endpoint: str,
        max_retries: int = 2,
        api_key: str | None = None,
    ):
        warn(
            "OpenAIAzureService is deprecated. Use LLMManager instead.",
            category=DeprecationWarning,
            stacklevel=1,
        )
        api_key = api_key or os.getenv("AZURE_OPENAI_KEY")
        client = openai.AzureOpenAI(
            azure_endpoint=azure_endpoint,
            api_version=api_version,
            api_key=api_key,
            max_retries=max_retries,
        )

        super().__init__(client=client, model_name=deployment_name)



def create_llm_instance(
    llm_deployment_name=settings.azure.llm_deployment_name,
    azure_openai_api_version=settings.azure.openai_api_version,
    max_retries=2,
) -> OpenAIAzureService:

    # TODO: temporary solution for staging issue
    llm_deployment_name = settings.azure.llm_deployment_name
    llm = OpenAIAzureService(
        deployment_name=llm_deployment_name,
        api_version=azure_openai_api_version,
        azure_endpoint=settings.azure.endpoint,
        max_retries=max_retries,
        api_key=settings.azure.active_azure_openai_key,
    )

    return llm