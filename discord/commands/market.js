const { SlashCommandBuilder } = require('@discordjs/builders');

module.exports = {
	data: new SlashCommandBuilder()
		.setName('market')
		.setDescription("Provide a price chart for all indexes in the server")
        .addStringOption(option =>
            option.setName('timespan')
                .setDescription("Timespan for the stock chart. Number of days, weeks, months, or years. Examples: 2d, 3w, 6m, 5y"))        
        ,
	async execute(interaction) {
		await interaction.reply('Not yet implemented');
	},
};