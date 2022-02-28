const { SlashCommandBuilder } = require('@discordjs/builders');

module.exports = {
	data: new SlashCommandBuilder()
		.setName('quote')
		.setDescription("Provide a price chart for one or more stocks or indexes")
        .addStringOption(option => 
            option.setName('tickers')
                .setDescription("Stock tickers or index identifiers to quote, comma-separated")
                .setRequired(true))
        .addStringOption(option =>
            option.setName('timespan')
                .setDescription("Timespan for the stock chart. Number of days, weeks, months, or years. Examples: 2d, 3w, 6m, 5y"))        
        ,
	async execute(interaction) {
		await interaction.reply('Not yet implemented');
	},
};