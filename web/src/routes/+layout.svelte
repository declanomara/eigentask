<script lang="ts">
    import "../app.css"; // relative path to your global CSS
</script>

<svelte:head>
    <!-- Open Graph/Twitter preview for iMessage and social cards -->
    <meta property="og:title" content="Eigentask" />
    <meta property="og:description" content="Plan tasks on a timeline with Eigentask." />
    <meta property="og:image" content="https://eigentask.com/landingpage.png" />
    <meta property="og:url" content="https://eigentask.com" />
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="Eigentask" />
    <meta name="twitter:description" content="Plan tasks on a timeline with Eigentask." />
    <meta name="twitter:image" content="https://eigentask.com/landingpage.png" />
</svelte:head>

<slot />
<!-- this renders the page content -->
